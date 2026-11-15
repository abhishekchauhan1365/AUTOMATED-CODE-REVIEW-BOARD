"""Finding deduplication tool for the Reviewer Manager."""

from __future__ import annotations

from difflib import SequenceMatcher

from orchestration.schemas import Finding, SEVERITY_ORDER


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./").lower()


def _lines_overlap(a: Finding, b: Finding, tolerance: int = 3) -> bool:
    if a.line_start is None or b.line_start is None:
        return a.line_start is None and b.line_start is None
    a_end = a.line_end if a.line_end is not None else a.line_start
    b_end = b.line_end if b.line_end is not None else b.line_start
    return not (a_end + tolerance < b.line_start or b_end + tolerance < a.line_start)


def _is_duplicate(a: Finding, b: Finding) -> bool:
    if _normalize_path(a.file_path) != _normalize_path(b.file_path):
        return False
    if not _lines_overlap(a, b, tolerance=3):
        return False

    # Same explicit rule ID
    if a.rule_id and b.rule_id and a.rule_id == b.rule_id:
        return True

    # Both flagging same SQLi / Shell / Secret / Eval concern at overlapping lines
    title_sim = SequenceMatcher(None, a.title.lower(), b.title.lower()).ratio()
    if title_sim >= 0.72:
        return True

    same_sec_bucket = (
        a.category == b.category == "security"
        and any(
            kw in a.title.lower() and kw in b.title.lower()
            for kw in ("sql", "shell", "eval", "exec", "secret", "password", "key", "pickle", "md5", "sha1", "verify")
        )
    )
    return same_sec_bucket


def deduplicate_findings(findings: list[Finding]) -> dict[str, object]:
    """Merge duplicate findings across agents while keeping highest severity and provenance."""
    unique: list[Finding] = []
    merged_count = 0

    for candidate in findings:
        matched_idx: int | None = None
        for idx, existing in enumerate(unique):
            if _is_duplicate(existing, candidate):
                matched_idx = idx
                break

        if matched_idx is None:
            copy = candidate.model_copy(deep=True)
            if copy.agent and copy.agent not in copy.corroborated_by:
                copy.corroborated_by = [copy.agent]
            unique.append(copy)
        else:
            merged_count += 1
            existing = unique[matched_idx]
            # Keep higher severity version as primary record
            if SEVERITY_ORDER[candidate.severity] > SEVERITY_ORDER[existing.severity]:
                merged_corroborators = list(dict.fromkeys(existing.corroborated_by + [candidate.agent]))
                replacement = candidate.model_copy(deep=True)
                replacement.corroborated_by = merged_corroborators
                unique[matched_idx] = replacement
            else:
                if candidate.agent not in existing.corroborated_by:
                    existing.corroborated_by.append(candidate.agent)
                if len(candidate.description) > len(existing.description):
                    existing.description = candidate.description

    return {
        "deduplicated_findings": unique,
        "original_count": len(findings),
        "deduplicated_count": len(unique),
        "duplicates_removed": merged_count,
    }

