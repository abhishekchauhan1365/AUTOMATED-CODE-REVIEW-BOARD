"""Source-code context extractor tool for Fix-Suggestion Agent."""

from __future__ import annotations

from typing import Any

from orchestration.schemas import SubmittedFile


def extract_code_context(
    files: list[SubmittedFile],
    file_path: str,
    line_start: int | None,
    line_end: int | None = None,
    context_lines: int = 8,
) -> dict[str, Any]:
    """Extract target code lines and surrounding context from submitted files."""
    target_file: SubmittedFile | None = None
    norm_target = file_path.replace("\\", "/").lstrip("./").lower()
    for sf in files:
        if sf.path.replace("\\", "/").lstrip("./").lower() == norm_target:
            target_file = sf
            break

    if target_file is None:
        return {
            "found": False,
            "file_path": file_path,
            "error": f"Source file '{file_path}' not available in submission.",
        }

    lines = target_file.content.splitlines()
    if not lines:
        return {
            "found": False,
            "file_path": target_file.path,
            "error": f"Source file '{target_file.path}' is empty.",
        }

    start = max(1, line_start or 1)
    end = max(start, min(len(lines), line_end or start))
    ctx_start = max(1, start - context_lines)
    ctx_end = min(len(lines), end + context_lines)

    target_block = "\n".join(lines[start - 1 : end])
    numbered_context = "\n".join(
        f"{idx:4d} | {lines[idx - 1]}" for idx in range(ctx_start, ctx_end + 1)
    )
    leading_indent = ""
    if lines[start - 1]:
        leading_indent = lines[start - 1][: len(lines[start - 1]) - len(lines[start - 1].lstrip())]

    return {
        "found": True,
        "file_path": target_file.path,
        "language": target_file.language,
        "full_content": target_file.content,
        "line_start": start,
        "line_end": end,
        "context_start": ctx_start,
        "context_end": ctx_end,
        "target_code": target_block,
        "numbered_context": numbered_context,
        "leading_indent": leading_indent,
        "total_lines": len(lines),
    }

