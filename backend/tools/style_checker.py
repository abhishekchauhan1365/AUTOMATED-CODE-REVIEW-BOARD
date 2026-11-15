"""Deterministic static style and linter tool (Ruff for Python + AST/regex rules)."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from orchestration.schemas import SubmittedFile


def _safe_write_temp_files(tmpdir: Path, files: list[SubmittedFile]) -> dict[Path, SubmittedFile]:
    """Write submitted files safely inside an isolated temporary directory without executing them."""
    mapping: dict[Path, SubmittedFile] = {}
    base = tmpdir.resolve()
    for sf in files:
        if sf.status == "deleted":
            continue
        target = (base / sf.path).resolve()
        if not str(target).startswith(str(base)):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(sf.content, encoding="utf-8")
        mapping[target] = sf
    return mapping


def _run_ruff_on_python_files(files: list[SubmittedFile]) -> tuple[list[dict[str, Any]], bool, str | None]:
    """Execute Ruff linter in isolated temp directory; returns (issues, ruff_available, error)."""
    py_files = [f for f in files if f.language == "python" and f.status != "deleted" and f.content.strip()]
    if not py_files:
        return [], True, None

    issues: list[dict[str, Any]] = []
    try:
        with tempfile.TemporaryDirectory(prefix="crb_ruff_") as tmp:
            tmp_path = Path(tmp)
            mapping = _safe_write_temp_files(tmp_path, py_files)
            if not mapping:
                return [], True, None

            cmd = [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--output-format",
                "json",
                "--select",
                "E,W,F,I,N,B,UP",
                "--no-cache",
                str(tmp_path),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
            raw_out = (proc.stdout or "").strip()
            if raw_out:
                parsed = json.loads(raw_out)
                for item in parsed:
                    filename = Path(item.get("filename", "")).resolve()
                    sf = mapping.get(filename)
                    rel_path = sf.path if sf else Path(item.get("filename", "unknown")).name
                    loc = item.get("location") or {}
                    end_loc = item.get("end_location") or loc
                    code = item.get("code") or "RUFF"
                    msg = item.get("message") or "Linting issue"
                    sev = "MEDIUM" if str(code).startswith(("F", "B", "E9")) else "LOW"
                    issues.append(
                        {
                            "rule_id": code,
                            "title": f"Ruff {code}: {msg[:80]}",
                            "description": msg,
                            "severity": sev,
                            "file_path": rel_path,
                            "line_start": loc.get("row"),
                            "line_end": end_loc.get("row"),
                            "tool": "ruff",
                        }
                    )
            return issues, True, None
    except FileNotFoundError:
        return [], False, "Ruff binary not found"
    except subprocess.TimeoutExpired:
        return [], False, "Ruff execution timed out"
    except Exception as exc:
        return [], False, f"Ruff analysis error: {exc}"


def _run_structural_style_checks(files: list[SubmittedFile]) -> list[dict[str, Any]]:
    """Run deterministic readability, naming, docstring, and line-length checks."""
    issues: list[dict[str, Any]] = []

    for sf in files:
        if sf.status == "deleted" or not sf.content.strip():
            continue

        lines = sf.content.splitlines()
        # Check overly long lines (> 120 chars)
        long_lines = [idx + 1 for idx, ln in enumerate(lines) if len(ln) > 120]
        if long_lines:
            issues.append(
                {
                    "rule_id": "STYLE-LINE-LEN",
                    "title": f"Long lines exceed 120 characters ({len(long_lines)} occurrences)",
                    "description": f"Lines {long_lines[:8]} exceed 120 characters, reducing readability.",
                    "severity": "LOW",
                    "file_path": sf.path,
                    "line_start": long_lines[0],
                    "line_end": long_lines[-1],
                    "tool": "style_checker",
                }
            )

        if sf.language == "python":
            try:
                tree = ast.parse(sf.content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        end_ln = getattr(node, "end_lineno", node.lineno)
                        fn_len = end_ln - node.lineno + 1
                        if fn_len > 50:
                            issues.append(
                                {
                                    "rule_id": "STYLE-LONG-FUNC",
                                    "title": f"Overly long function '{node.name}' ({fn_len} lines)",
                                    "description": (
                                        f"Function '{node.name}' spans {fn_len} lines (> 50). "
                                        "Consider decomposing into smaller single-purpose helpers."
                                    ),
                                    "severity": "MEDIUM",
                                    "file_path": sf.path,
                                    "line_start": node.lineno,
                                    "line_end": end_ln,
                                    "tool": "style_checker",
                                }
                            )
                        if not node.name.startswith("_") and not re.match(r"^[a-z_][a-z0-9_]*$", node.name):
                            issues.append(
                                {
                                    "rule_id": "STYLE-NAMING",
                                    "title": f"Non-snake_case function name '{node.name}'",
                                    "description": f"Python function '{node.name}' violates PEP 8 snake_case naming.",
                                    "severity": "LOW",
                                    "file_path": sf.path,
                                    "line_start": node.lineno,
                                    "line_end": node.lineno,
                                    "tool": "style_checker",
                                }
                            )
                        if not node.name.startswith("_") and ast.get_docstring(node) is None and fn_len >= 8:
                            issues.append(
                                {
                                    "rule_id": "STYLE-DOCSTRING",
                                    "title": f"Missing docstring on function '{node.name}'",
                                    "description": f"Public function '{node.name}' lacks a concise docstring.",
                                    "severity": "INFO",
                                    "file_path": sf.path,
                                    "line_start": node.lineno,
                                    "line_end": node.lineno,
                                    "tool": "style_checker",
                                }
                            )
                    elif isinstance(node, ast.ClassDef):
                        if not re.match(r"^[A-Z][A-Za-z0-9]*$", node.name):
                            issues.append(
                                {
                                    "rule_id": "STYLE-CLASS-NAME",
                                    "title": f"Non-PascalCase class name '{node.name}'",
                                    "description": f"Class '{node.name}' should follow PEP 8 CapWords/PascalCase.",
                                    "severity": "LOW",
                                    "file_path": sf.path,
                                    "line_start": node.lineno,
                                    "line_end": node.lineno,
                                    "tool": "style_checker",
                                }
                            )
            except SyntaxError:
                pass
        elif sf.language in ("javascript", "typescript"):
            for idx, ln in enumerate(lines, start=1):
                if re.search(r"\bvar\s+\w+", ln):
                    issues.append(
                        {
                            "rule_id": "JS-NO-VAR",
                            "title": "Use 'const' or 'let' instead of 'var'",
                            "description": "Function-scoped 'var' can introduce hoisting bugs.",
                            "severity": "LOW",
                            "file_path": sf.path,
                            "line_start": idx,
                            "line_end": idx,
                            "tool": "style_checker",
                        }
                    )
                if "console.log(" in ln:
                    issues.append(
                        {
                            "rule_id": "JS-CONSOLE-LOG",
                            "title": "Debug console.log statement left in code",
                            "description": "Remove debug console.log calls or replace with structured logger.",
                            "severity": "INFO",
                            "file_path": sf.path,
                            "line_start": idx,
                            "line_end": idx,
                            "tool": "style_checker",
                        }
                    )

    return issues


def run_linter(files: list[SubmittedFile]) -> dict[str, Any]:
    """Run deterministic linting (Ruff + structural style checks) on submitted files."""
    ruff_issues, ruff_ok, ruff_err = _run_ruff_on_python_files(files)
    structural_issues = _run_structural_style_checks(files)
    all_issues = ruff_issues + structural_issues

    return {
        "issues": all_issues,
        "ruff_executed": ruff_ok,
        "ruff_error": ruff_err,
        "total_issues": len(all_issues),
    }

