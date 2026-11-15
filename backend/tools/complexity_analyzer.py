"""Code complexity (Radon/AST) and duplication analyzer tool."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from radon.complexity import cc_visit

from orchestration.schemas import SubmittedFile


def _detect_duplication(files: list[SubmittedFile], window_size: int = 5) -> list[dict[str, Any]]:
    """Detect duplicated normalized code blocks (>= window_size non-trivial lines)."""
    seen_blocks: dict[str, list[dict[str, Any]]] = {}
    duplicates: list[dict[str, Any]] = []

    for sf in files:
        if sf.status == "deleted" or not sf.content.strip():
            continue

        clean_lines: list[tuple[int, str]] = []
        for idx, raw in enumerate(sf.content.splitlines(), start=1):
            norm = re.sub(r"\s+", " ", raw.strip())
            if norm and not norm.startswith(("#", "//", "/*", "*", "import ", "from ")):
                clean_lines.append((idx, norm))

        if len(clean_lines) < window_size:
            continue

        for i in range(len(clean_lines) - window_size + 1):
            chunk = clean_lines[i : i + window_size]
            joined = "\n".join(text for _, text in chunk)
            if len(joined) < 60:
                continue
            digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]
            seen_blocks.setdefault(digest, []).append(
                {
                    "file_path": sf.path,
                    "line_start": chunk[0][0],
                    "line_end": chunk[-1][0],
                    "preview": chunk[0][1][:90],
                }
            )

    reported_pairs: set[tuple[str, int]] = set()
    for digest, occurrences in seen_blocks.items():
        if len(occurrences) >= 2:
            first = occurrences[0]
            second = occurrences[1]
            # Avoid overlapping self-matches within 2 lines
            if first["file_path"] == second["file_path"] and abs(first["line_start"] - second["line_start"]) < window_size:
                continue
            key = (second["file_path"], second["line_start"])
            if key in reported_pairs:
                continue
            reported_pairs.add(key)
            duplicates.append(
                {
                    "rule_id": f"DUP-{digest[:6]}",
                    "title": f"Duplicated code block detected across {len(occurrences)} locations",
                    "description": (
                        f"A {window_size}+ line logic block starting at {first['file_path']}:{first['line_start']} "
                        f"is duplicated at {second['file_path']}:{second['line_start']}."
                    ),
                    "severity": "LOW",
                    "file_path": second["file_path"],
                    "line_start": second["line_start"],
                    "line_end": second["line_end"],
                    "evidence": second["preview"],
                }
            )

    return duplicates


def calculate_complexity(files: list[SubmittedFile]) -> dict[str, Any]:
    """Compute cyclomatic complexity (via Radon for Python) and detect code duplication."""
    complexity_issues: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []

    for sf in files:
        if sf.status == "deleted" or not sf.content.strip():
            continue

        if sf.language == "python":
            try:
                blocks = cc_visit(sf.content)
                for blk in blocks:
                    metrics.append(
                        {
                            "file_path": sf.path,
                            "name": blk.name,
                            "complexity": blk.complexity,
                            "line_start": blk.lineno,
                            "line_end": getattr(blk, "endline", blk.lineno),
                        }
                    )
                    if blk.complexity >= 10:
                        sev = "HIGH" if blk.complexity >= 16 else "MEDIUM"
                        complexity_issues.append(
                            {
                                "rule_id": "COMPLEXITY-CC",
                                "title": f"High cyclomatic complexity ({blk.complexity}) in '{blk.name}'",
                                "description": (
                                    f"'{blk.name}' has cyclomatic complexity {blk.complexity} (>= 10), "
                                    "making it harder to read, reason about, and test thoroughly."
                                ),
                                "severity": sev,
                                "file_path": sf.path,
                                "line_start": blk.lineno,
                                "line_end": getattr(blk, "endline", blk.lineno),
                            }
                        )
            except SyntaxError:
                pass
        else:
            # Deterministic branch counting for non-Python files
            branch_count = len(re.findall(r"\b(if|else if|for|while|case|catch|&&|\|\||\?)\b", sf.content)) + 1
            metrics.append(
                {
                    "file_path": sf.path,
                    "name": sf.path,
                    "complexity": branch_count,
                    "line_start": 1,
                    "line_end": len(sf.content.splitlines()),
                }
            )
            if branch_count >= 15:
                complexity_issues.append(
                    {
                        "rule_id": "COMPLEXITY-BRANCH",
                        "title": f"High branching complexity ({branch_count}) in {sf.path}",
                        "description": f"File contains {branch_count} control-flow branches; consider modularizing.",
                        "severity": "MEDIUM",
                        "file_path": sf.path,
                        "line_start": 1,
                        "line_end": len(sf.content.splitlines()),
                    }
                )

    duplication_issues = _detect_duplication(files)
    return {
        "metrics": metrics,
        "complexity_issues": complexity_issues,
        "duplication_issues": duplication_issues,
    }

