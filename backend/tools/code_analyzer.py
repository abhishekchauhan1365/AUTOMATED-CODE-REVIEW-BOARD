"""File and code structure analyzer tool using Python AST and multi-language heuristics."""

from __future__ import annotations

import ast
import re
from typing import Any

from orchestration.schemas import SubmittedFile


_RISKY_CALL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(eval|exec|compile)\s*\("), "Dynamic code execution"),
    (re.compile(r"\b(subprocess\.(run|Popen|call|check_output)|os\.system|os\.popen)\b"), "OS command / subprocess invocation"),
    (re.compile(r"\b(pickle\.loads?|yaml\.load|marshal\.loads?)\b"), "Unsafe deserialization"),
    (re.compile(r"\b(execute|executemany|raw)\s*\("), "Database query execution"),
    (re.compile(r"\b(password|secret|token|jwt|auth|login|verify_signature|chmod|chown)\b", re.I), "Authentication / security-sensitive logic"),
]


def _analyze_python_ast(sf: SubmittedFile) -> dict[str, Any]:
    functions: list[dict[str, Any]] = []
    classes: list[dict[str, Any]] = []
    imports: list[str] = []
    syntax_error: str | None = None

    try:
        tree = ast.parse(sf.content)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end_line = getattr(node, "end_lineno", node.lineno)
                functions.append(
                    {
                        "name": node.name,
                        "line_start": node.lineno,
                        "line_end": end_line,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "args": [a.arg for a in node.args.args],
                    }
                )
            elif isinstance(node, ast.ClassDef):
                end_line = getattr(node, "end_lineno", node.lineno)
                classes.append(
                    {
                        "name": node.name,
                        "line_start": node.lineno,
                        "line_end": end_line,
                    }
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    imports.append(f"{mod}.{alias.name}".strip("."))
    except SyntaxError as exc:
        syntax_error = f"Line {exc.lineno}: {exc.msg}"

    return {
        "functions": sorted(functions, key=lambda x: x["line_start"]),
        "classes": sorted(classes, key=lambda x: x["line_start"]),
        "imports": sorted(set(imports)),
        "syntax_error": syntax_error,
    }


def _analyze_generic_structure(sf: SubmittedFile) -> dict[str, Any]:
    functions: list[dict[str, Any]] = []
    classes: list[dict[str, Any]] = []
    imports: list[str] = []

    fn_patterns = [
        re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_]\w*)\s*\("),
        re.compile(r"^\s*(?:export\s+)?(?:const|let)\s+([A-Za-z_]\w*)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>"),
        re.compile(r"^\s*(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{"),
        re.compile(r"^\s*func\s+(?:\([^)]+\)\s*)?([A-Za-z_]\w*)\s*\("),
    ]
    cls_pattern = re.compile(r"^\s*(?:export\s+)?(?:abstract\s+)?(?:class|interface|struct)\s+([A-Za-z_]\w*)")
    imp_pattern = re.compile(r"^\s*(?:import|from|#include|using)\s+(.+)$")

    for idx, line in enumerate(sf.content.splitlines(), start=1):
        for pat in fn_patterns:
            m = pat.match(line)
            if m:
                functions.append({"name": m.group(1), "line_start": idx, "line_end": idx, "is_async": "async" in line, "args": []})
                break
        cm = cls_pattern.match(line)
        if cm:
            classes.append({"name": cm.group(1), "line_start": idx, "line_end": idx})
        im = imp_pattern.match(line)
        if im:
            imports.append(im.group(1).strip()[:80])

    return {"functions": functions, "classes": classes, "imports": imports, "syntax_error": None}


def analyze_code_structure(files: list[SubmittedFile]) -> dict[str, Any]:
    """Analyze functions, classes, imports, line counts, and risky structural patterns."""
    file_structures: list[dict[str, Any]] = []
    important_functions: list[dict[str, Any]] = []
    risky_changes: list[dict[str, Any]] = []

    for sf in files:
        if sf.status == "deleted":
            continue

        struct = _analyze_python_ast(sf) if sf.language == "python" else _analyze_generic_structure(sf)
        lines = sf.content.splitlines()

        for fn in struct["functions"]:
            important_functions.append(
                {
                    "file_path": sf.path,
                    "name": fn["name"],
                    "line_start": fn["line_start"],
                    "line_end": fn["line_end"],
                }
            )

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "//", "/*", "*")):
                continue
            for pat, reason in _RISKY_CALL_PATTERNS:
                if pat.search(line):
                    risky_changes.append(
                        {
                            "file_path": sf.path,
                            "line": idx,
                            "reason": reason,
                            "snippet": stripped[:140],
                        }
                    )
                    break

        file_structures.append(
            {
                "path": sf.path,
                "language": sf.language,
                "line_count": len(lines),
                "functions": struct["functions"],
                "classes": struct["classes"],
                "imports": struct["imports"],
                "syntax_error": struct["syntax_error"],
            }
        )

    return {
        "files": file_structures,
        "important_functions": important_functions,
        "risky_changes": risky_changes,
    }

