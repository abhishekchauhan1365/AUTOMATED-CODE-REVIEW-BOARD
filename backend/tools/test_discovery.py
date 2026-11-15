"""Test-file discovery and symbol-to-test mapping tool."""

from __future__ import annotations

import ast
import re
from pathlib import PurePosixPath
from typing import Any

from orchestration.schemas import SubmittedFile


def is_test_file(path: str) -> bool:
    """Return True if path matches standard test file naming conventions."""
    lower = path.lower().replace("\\", "/")
    name = PurePosixPath(lower).name
    if "/tests/" in f"/{lower}" or "/__tests__/" in f"/{lower}":
        return True
    if name.startswith("test_") or name.endswith("_test.py") or name.endswith("_test.go"):
        return True
    if ".test." in name or ".spec." in name or name.endswith("test.java") or name.endswith("tests.java"):
        return True
    return False


def _extract_test_cases(sf: SubmittedFile) -> list[str]:
    cases: list[str] = []
    if sf.language == "python":
        try:
            tree = ast.parse(sf.content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                    cases.append(node.name)
        except SyntaxError:
            pass
    else:
        for m in re.finditer(r"""\b(?:it|test|describe)\s*\(\s*['"]([^'"]+)['"]""", sf.content):
            cases.append(m.group(1))
        for m in re.finditer(r"""\bfunc\s+(Test[A-Za-z0-9_]+)\s*\(""", sf.content):
            cases.append(m.group(1))
    return cases


def _extract_production_symbols(sf: SubmittedFile) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    if sf.language == "python":
        try:
            tree = ast.parse(sf.content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith("_"):
                        symbols.append(
                            {
                                "name": node.name,
                                "file_path": sf.path,
                                "line_start": node.lineno,
                                "line_end": getattr(node, "end_lineno", node.lineno),
                            }
                        )
        except SyntaxError:
            pass
    else:
        for idx, line in enumerate(sf.content.splitlines(), start=1):
            m = re.match(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_]\w*)\s*\(", line)
            if m:
                symbols.append({"name": m.group(1), "file_path": sf.path, "line_start": idx, "line_end": idx})
            gm = re.match(r"^\s*func\s+([A-Z]\w*)\s*\(", line)
            if gm:
                symbols.append({"name": gm.group(1), "file_path": sf.path, "line_start": idx, "line_end": idx})
    return symbols


def discover_test_files(files: list[SubmittedFile]) -> dict[str, Any]:
    """Identify test files, extract test cases, and map production symbols to tests."""
    test_files: list[dict[str, Any]] = []
    production_files: list[SubmittedFile] = []
    all_test_corpus = ""

    for sf in files:
        if sf.status == "deleted":
            continue
        if is_test_file(sf.path):
            cases = _extract_test_cases(sf)
            test_files.append(
                {
                    "path": sf.path,
                    "language": sf.language,
                    "test_cases": cases,
                    "test_count": len(cases),
                }
            )
            all_test_corpus += "\n" + sf.content
        elif sf.language in ("python", "javascript", "typescript", "java", "go", "c", "cpp"):
            production_files.append(sf)

    tested_symbols: list[dict[str, Any]] = []
    untested_symbols: list[dict[str, Any]] = []

    for prod in production_files:
        symbols = _extract_production_symbols(prod)
        for sym in symbols:
            # Check exact word reference in submitted test files
            pattern = re.compile(rf"\b{re.escape(sym['name'])}\b")
            if all_test_corpus and pattern.search(all_test_corpus):
                tested_symbols.append(sym)
            else:
                untested_symbols.append(sym)

    return {
        "test_files": test_files,
        "production_files": [p.path for p in production_files],
        "tested_symbols": tested_symbols,
        "untested_symbols": untested_symbols,
        "has_tests": len(test_files) > 0,
    }

