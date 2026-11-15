"""Unified diff patch generator and static validator (never executes patches)."""

from __future__ import annotations

import ast
import difflib
import re
from typing import Any


def generate_unified_patch(
    file_path: str,
    original_content: str,
    replacement_block: str,
    line_start: int,
    line_end: int,
) -> dict[str, Any]:
    """Generate a unified diff patch replacing [line_start..line_end] without altering original files."""
    orig_lines = original_content.splitlines(keepends=True)
    if not orig_lines:
        return {"success": False, "error": "Original file content is empty.", "patch": "", "patched_content": ""}

    start_idx = max(0, line_start - 1)
    end_idx = min(len(orig_lines), max(line_start, line_end))

    replacement_lines = [
        ln + "\n" for ln in replacement_block.splitlines()
    ]
    # Preserve trailing newline behavior if original ended without newline
    if replacement_lines and orig_lines and not orig_lines[-1].endswith("\n") and end_idx == len(orig_lines):
        replacement_lines[-1] = replacement_lines[-1].rstrip("\n")

    new_lines = orig_lines[:start_idx] + replacement_lines + orig_lines[end_idx:]
    patched_content = "".join(new_lines)

    diff_iter = difflib.unified_diff(
        orig_lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        n=3,
    )
    patch_text = "".join(diff_iter)
    return {
        "success": bool(patch_text.strip()),
        "patch": patch_text,
        "patched_content": patched_content,
        "original_block": "".join(orig_lines[start_idx:end_idx]).rstrip("\n"),
    }


def validate_patch(
    file_path: str,
    patched_content: str,
    patch_text: str,
    language: str = "python",
) -> dict[str, Any]:
    """Statically validate unified diff headers/hunks and resulting syntax without executing code."""
    if not patch_text or not patch_text.strip():
        return {"valid": False, "status": "invalid", "message": "Generated patch is empty (no changes)."}

    has_headers = ("--- a/" in patch_text) and ("+++ b/" in patch_text)
    has_hunk = bool(re.search(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@", patch_text, flags=re.MULTILINE))
    if not (has_headers and has_hunk):
        return {
            "valid": False,
            "status": "invalid",
            "message": "Patch is missing valid unified diff headers or @@ hunk markers.",
        }

    if language == "python" or file_path.endswith(".py"):
        try:
            ast.parse(patched_content)
        except SyntaxError as exc:
            return {
                "valid": False,
                "status": "invalid",
                "message": f"Patched Python code failed AST syntax validation at line {exc.lineno}: {exc.msg}",
            }

    return {
        "valid": True,
        "status": "valid",
        "message": "Unified diff format and static syntax validation passed (not executed).",
    }

