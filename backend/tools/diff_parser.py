"""Git diff parser and modified-file extraction tools."""

from __future__ import annotations

import difflib
import re
from typing import Any

from orchestration.schemas import SubmittedFile
from services.file_service import detect_language, sanitize_relative_path


_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


def parse_git_diff(diff_text: str) -> dict[str, Any]:
    """Parse a unified Git diff into structured file entries, hunks, and added/removed lines."""
    if not diff_text or not diff_text.strip():
        return {"files": [], "total_additions": 0, "total_deletions": 0, "parse_warnings": ["Empty diff provided."]}

    lines = diff_text.splitlines()
    files: list[dict[str, Any]] = []
    current_file: dict[str, Any] | None = None
    current_hunk: dict[str, Any] | None = None
    new_line_no = 0
    old_line_no = 0
    total_additions = 0
    total_deletions = 0
    warnings: list[str] = []

    def _flush_hunk() -> None:
        nonlocal current_hunk
        if current_file is not None and current_hunk is not None:
            current_file["hunks"].append(current_hunk)
            current_hunk = None

    def _flush_file() -> None:
        nonlocal current_file
        _flush_hunk()
        if current_file is not None:
            files.append(current_file)
            current_file = None

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("diff --git "):
            _flush_file()
            parts = line.split()
            raw_path = parts[-1] if len(parts) >= 4 else "unknown"
            if raw_path.startswith("b/"):
                raw_path = raw_path[2:]
            try:
                safe_path = sanitize_relative_path(raw_path)
            except Exception:
                safe_path = raw_path.lstrip("/")
            current_file = {
                "path": safe_path,
                "status": "modified",
                "language": detect_language(safe_path),
                "additions": 0,
                "deletions": 0,
                "hunks": [],
                "added_lines": [],
                "removed_lines": [],
                "reconstructed_lines": {},
            }
            i += 1
            continue

        if line.startswith("new file mode"):
            if current_file is not None:
                current_file["status"] = "added"
            i += 1
            continue

        if line.startswith("deleted file mode"):
            if current_file is not None:
                current_file["status"] = "deleted"
            i += 1
            continue

        if line.startswith("--- "):
            old_path = line[4:].strip()
            if current_file is None:
                # Unified diff without "diff --git" header
                next_line = lines[i + 1] if i + 1 < len(lines) else ""
                candidate = next_line[4:].strip() if next_line.startswith("+++ ") else old_path
                if candidate.startswith(("a/", "b/")):
                    candidate = candidate[2:]
                if candidate == "/dev/null" and old_path.startswith("a/"):
                    candidate = old_path[2:]
                try:
                    safe_path = sanitize_relative_path(candidate)
                except Exception:
                    safe_path = candidate or "patch_target.py"
                current_file = {
                    "path": safe_path,
                    "status": "added" if old_path == "/dev/null" else "modified",
                    "language": detect_language(safe_path),
                    "additions": 0,
                    "deletions": 0,
                    "hunks": [],
                    "added_lines": [],
                    "removed_lines": [],
                    "reconstructed_lines": {},
                }
            elif old_path == "/dev/null":
                current_file["status"] = "added"
            i += 1
            continue

        if line.startswith("+++ "):
            new_path = line[4:].strip()
            if current_file is not None:
                if new_path == "/dev/null":
                    current_file["status"] = "deleted"
                else:
                    clean_p = new_path[2:] if new_path.startswith("b/") else new_path
                    if clean_p and clean_p != "/dev/null":
                        try:
                            current_file["path"] = sanitize_relative_path(clean_p)
                        except Exception:
                            current_file["path"] = clean_p
                        current_file["language"] = detect_language(current_file["path"])
            i += 1
            continue

        hunk_match = _HUNK_RE.match(line)
        if hunk_match:
            _flush_hunk()
            if current_file is None:
                current_file = {
                    "path": "submitted_diff.py",
                    "status": "modified",
                    "language": "python",
                    "additions": 0,
                    "deletions": 0,
                    "hunks": [],
                    "added_lines": [],
                    "removed_lines": [],
                    "reconstructed_lines": {},
                }
            old_line_no = int(hunk_match.group(1))
            new_line_no = int(hunk_match.group(3))
            current_hunk = {
                "header": line,
                "old_start": old_line_no,
                "new_start": new_line_no,
                "context": hunk_match.group(5).strip(),
                "lines": [],
            }
            i += 1
            continue

        if current_hunk is not None and current_file is not None:
            if line.startswith("+") and not line.startswith("+++"):
                content = line[1:]
                current_file["additions"] += 1
                total_additions += 1
                current_file["added_lines"].append({"line": new_line_no, "content": content})
                current_file["reconstructed_lines"][new_line_no] = content
                current_hunk["lines"].append({"type": "add", "line": new_line_no, "content": content})
                new_line_no += 1
            elif line.startswith("-") and not line.startswith("---"):
                content = line[1:]
                current_file["deletions"] += 1
                total_deletions += 1
                current_file["removed_lines"].append({"line": old_line_no, "content": content})
                current_hunk["lines"].append({"type": "del", "line": old_line_no, "content": content})
                old_line_no += 1
            elif line.startswith(" ") or line == "":
                content = line[1:] if line.startswith(" ") else ""
                current_file["reconstructed_lines"][new_line_no] = content
                current_hunk["lines"].append({"type": "ctx", "line": new_line_no, "content": content})
                new_line_no += 1
                old_line_no += 1
            elif line.startswith("\\ No newline"):
                pass
            else:
                warnings.append(f"Ignored unrecognized diff line {i + 1}: {line[:60]}")
        i += 1

    _flush_file()

    # Build reconstructed source text per file so downstream static tools can inspect line numbers accurately
    for f in files:
        line_map: dict[int, str] = f.pop("reconstructed_lines", {})
        if line_map:
            max_ln = max(line_map.keys())
            buf = [""] * max_ln
            for ln, txt in line_map.items():
                if 1 <= ln <= max_ln:
                    buf[ln - 1] = txt
            f["reconstructed_content"] = "\n".join(buf)
        else:
            f["reconstructed_content"] = ""

    return {
        "files": files,
        "total_additions": total_additions,
        "total_deletions": total_deletions,
        "parse_warnings": warnings,
    }


def extract_modified_files(
    git_diff: str | None = None,
    submitted_files: list[SubmittedFile] | None = None,
) -> dict[str, Any]:
    """Extract normalized SubmittedFile records and a unified diff representation."""
    files_list = list(submitted_files or [])
    diff_summary: dict[str, Any]

    if git_diff and git_diff.strip():
        diff_summary = parse_git_diff(git_diff)
        if not files_list:
            for item in diff_summary["files"]:
                content = item.get("reconstructed_content", "")
                files_list.append(
                    SubmittedFile(
                        path=item["path"],
                        language=item.get("language") or detect_language(item["path"]),
                        content=content,
                        size_bytes=len(content.encode("utf-8")),
                        status=item.get("status", "modified"),
                    )
                )
    else:
        # Synthesize unified diff from uploaded files so Diff Agent always has hunks
        synth_chunks: list[str] = []
        parsed_entries: list[dict[str, Any]] = []
        total_add = 0
        for sf in files_list:
            lines = sf.content.splitlines(keepends=True)
            diff_lines = list(
                difflib.unified_diff(
                    [],
                    lines,
                    fromfile="/dev/null" if sf.status == "added" else f"a/{sf.path}",
                    tofile=f"b/{sf.path}",
                    lineterm="",
                )
            )
            synth_chunks.append("\n".join(diff_lines))
            add_count = len(sf.content.splitlines())
            total_add += add_count
            parsed_entries.append(
                {
                    "path": sf.path,
                    "status": sf.status,
                    "language": sf.language,
                    "additions": add_count,
                    "deletions": 0,
                    "hunks": [],
                    "added_lines": [
                        {"line": idx + 1, "content": line}
                        for idx, line in enumerate(sf.content.splitlines())
                    ],
                    "removed_lines": [],
                    "reconstructed_content": sf.content,
                }
            )
        diff_summary = {
            "files": parsed_entries,
            "total_additions": total_add,
            "total_deletions": 0,
            "parse_warnings": [],
            "synthesized_diff": "\n".join(synth_chunks),
        }

    return {
        "submitted_files": files_list,
        "file_records": [
            {
                "path": f["path"],
                "status": f["status"],
                "language": f["language"],
                "additions": f["additions"],
                "deletions": f["deletions"],
            }
            for f in diff_summary["files"]
        ],
        "diff_summary": diff_summary,
    }

