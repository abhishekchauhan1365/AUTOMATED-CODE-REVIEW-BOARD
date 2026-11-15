"""Static security vulnerability scanner (Bandit for Python + AST/pattern detectors)."""

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
from services.file_service import redact_secrets_in_text


def _safe_write_temp(tmpdir: Path, files: list[SubmittedFile]) -> dict[Path, SubmittedFile]:
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


def _run_bandit(files: list[SubmittedFile]) -> tuple[list[dict[str, Any]], bool, str | None]:
    """Run Bandit static AST security analyzer on Python files without executing them."""
    py_files = [f for f in files if f.language == "python" and f.status != "deleted" and f.content.strip()]
    if not py_files:
        return [], True, None

    findings: list[dict[str, Any]] = []
    try:
        with tempfile.TemporaryDirectory(prefix="crb_bandit_") as tmp:
            tmp_path = Path(tmp)
            mapping = _safe_write_temp(tmp_path, py_files)
            if not mapping:
                return [], True, None

            cmd = [sys.executable, "-m", "bandit", "-r", "-f", "json", "-q", str(tmp_path)]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=25, check=False)
            raw = (proc.stdout or "").strip()
            if raw:
                data = json.loads(raw)
                for res in data.get("results", []):
                    test_id = res.get("test_id", "BANDIT")
                    # Skip B101 assert warnings in test files
                    resolved_file = Path(res.get("filename", "")).resolve()
                    sf = mapping.get(resolved_file)
                    rel_path = sf.path if sf else Path(res.get("filename", "unknown")).name
                    if test_id == "B101" and ("test" in rel_path.lower()):
                        continue

                    bandit_sev = str(res.get("issue_severity", "MEDIUM")).upper()
                    sev_map = {"HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}
                    norm_sev = sev_map.get(bandit_sev, "MEDIUM")
                    if test_id in ("B102", "B301", "B307", "B602", "B605", "B608"):
                        # Elevate critical command/code/SQL injection patterns
                        if bandit_sev == "HIGH":
                            norm_sev = "CRITICAL"

                    line_num = res.get("line_number")
                    findings.append(
                        {
                            "rule_id": test_id,
                            "title": f"Bandit {test_id}: {res.get('issue_text', 'Security issue')[:85]}",
                            "description": res.get("issue_text", "Potential security vulnerability detected by Bandit."),
                            "severity": norm_sev,
                            "file_path": rel_path,
                            "line_start": line_num,
                            "line_end": line_num,
                            "evidence": redact_secrets_in_text((res.get("code") or "").strip())[:180],
                            "recommended_action": (
                                f"Address Bandit rule {test_id} ({res.get('test_name', '')}); "
                                "use safe parameterized or non-shell APIs."
                            ),
                            "tool": "bandit",
                        }
                    )
            return findings, True, None
    except FileNotFoundError:
        return [], False, "Bandit not installed"
    except subprocess.TimeoutExpired:
        return [], False, "Bandit timed out"
    except Exception as exc:
        return [], False, f"Bandit error: {exc}"


def _run_pattern_security_checks(files: list[SubmittedFile]) -> list[dict[str, Any]]:
    """Run deterministic AST and regex checks for SQLi, shell injection, XSS, unsafe functions."""
    findings: list[dict[str, Any]] = []

    rules: list[tuple[str, str, re.Pattern[str], str, str, str]] = [
        (
            "SEC-SQLI-FMT",
            "Potential SQL Injection via dynamic string interpolation",
            re.compile(
                r"""(?:execute|executemany|raw|query)\s*\(\s*(?:f['"]|['"].*%s.*['"]\s*%|['"].*['"]\s*\+|\s*`[^`]*\$\{)"""
            ),
            "CRITICAL",
            "Constructing SQL queries using f-strings, string concatenation, or template interpolation enables SQL injection.",
            "Use parameterized queries / prepared statements (e.g., cursor.execute('SELECT ... WHERE id = ?', (user_id,))).",
        ),
        (
            "SEC-SQLI-CONCAT",
            "Dynamic SQL query string concatenation",
            re.compile(r"""(?i)(?:SELECT|INSERT|UPDATE|DELETE)\b[^;\n]*(?:\+\s*[A-Za-z_]\w*|\{[A-Za-z_]\w*\}|%s)"""),
            "HIGH",
            "SQL statement appears to concatenate or interpolate variables directly into the query string.",
            "Replace interpolated SQL strings with parameterized query bindings.",
        ),
        (
            "SEC-SHELL-TRUE",
            "Dangerous shell execution with shell=True / os.system",
            re.compile(r"""(?:subprocess\.(?:run|Popen|call|check_output|check_call)\([^)]*shell\s*=\s*True|\bos\.system\s*\(|\bos\.popen\s*\()"""),
            "CRITICAL",
            "Invoking a system shell with potentially untrusted input exposes the application to OS command injection.",
            "Pass argument lists directly to subprocess.run([...], shell=False) and validate inputs.",
        ),
        (
            "SEC-EVAL-EXEC",
            "Unsafe dynamic code execution (eval / exec)",
            re.compile(r"""\b(?:eval|exec)\s*\("""),
            "CRITICAL",
            "Calling eval() or exec() can execute arbitrary attacker-controlled code.",
            "Replace eval()/exec() with ast.literal_eval() for data parsing or explicit dispatch tables.",
        ),
        (
            "SEC-PICKLE",
            "Unsafe deserialization via pickle / yaml.load",
            re.compile(r"""\b(?:pickle\.loads?|cPickle\.loads?|marshal\.loads?|yaml\.load\s*\([^)]*(?!Loader\s*=\s*yaml\.SafeLoader))\b"""),
            "HIGH",
            "Deserializing untrusted payloads with pickle or unsafe yaml.load enables remote code execution.",
            "Use json.loads() or yaml.safe_load() instead.",
        ),
        (
            "SEC-TLS-VERIFY",
            "TLS certificate verification disabled (verify=False)",
            re.compile(r"""verify\s*=\s*False"""),
            "HIGH",
            "Disabling SSL/TLS certificate validation exposes traffic to man-in-the-middle attacks.",
            "Keep verify=True and configure trusted CA certificates.",
        ),
        (
            "SEC-WEAK-HASH",
            "Use of weak cryptographic hash (MD5 / SHA-1)",
            re.compile(r"""\bhashlib\.(?:md5|sha1)\s*\("""),
            "MEDIUM",
            "MD5 and SHA-1 are cryptographically broken for passwords and integrity verification.",
            "Use hashlib.sha256() for integrity or bcrypt/argon2/pbkdf2_hmac for passwords.",
        ),
        (
            "SEC-XSS-DOM",
            "Potential DOM XSS sink (innerHTML / dangerouslySetInnerHTML)",
            re.compile(r"""(?:\.innerHTML\s*=|dangerouslySetInnerHTML)"""),
            "HIGH",
            "Assigning raw HTML directly to the DOM can lead to Cross-Site Scripting (XSS).",
            "Use textContent/safe JSX rendering or sanitize HTML with DOMPurify.",
        ),
        (
            "SEC-C-UNSAFE",
            "Unsafe C/C++ buffer function (gets / strcpy / sprintf)",
            re.compile(r"""\b(?:gets|strcpy|strcat|sprintf)\s*\("""),
            "CRITICAL",
            "Unbounded C string/buffer functions cause stack/heap buffer overflows.",
            "Replace with bounded equivalents (fgets, strncpy/strlcpy, snprintf).",
        ),
    ]

    for sf in files:
        if sf.status == "deleted" or not sf.content.strip():
            continue
        lines = sf.content.splitlines()
        for line_no, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            if not stripped or stripped.startswith(("#", "//", "/*", "*")):
                continue
            for rule_id, title, pat, sev, desc, action in rules:
                if pat.search(raw_line):
                    # Avoid double-reporting yaml.safe_load
                    if rule_id == "SEC-PICKLE" and ("yaml.safe_load" in raw_line or "SafeLoader" in raw_line):
                        continue
                    findings.append(
                        {
                            "rule_id": rule_id,
                            "title": title,
                            "description": desc,
                            "severity": sev,
                            "file_path": sf.path,
                            "line_start": line_no,
                            "line_end": line_no,
                            "evidence": redact_secrets_in_text(stripped)[:180],
                            "recommended_action": action,
                            "tool": "security_pattern_scanner",
                        }
                    )

        # Python AST check for multi-line f-string SQL execution
        if sf.language == "python":
            try:
                tree = ast.parse(sf.content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                        if node.func.attr in ("execute", "executemany") and node.args:
                            arg0 = node.args[0]
                            if isinstance(arg0, (ast.JoinedStr, ast.BinOp)):
                                findings.append(
                                    {
                                        "rule_id": "SEC-AST-SQLI",
                                        "title": "Parameterized query violation in cursor.execute()",
                                        "description": (
                                            f"AST inspection detected dynamic string construction inside "
                                            f"'.{node.func.attr}()' at line {node.lineno}."
                                        ),
                                        "severity": "CRITICAL",
                                        "file_path": sf.path,
                                        "line_start": node.lineno,
                                        "line_end": getattr(node, "end_lineno", node.lineno),
                                        "evidence": redact_secrets_in_text(
                                            lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
                                        )[:180],
                                        "recommended_action": "Pass SQL parameters as a tuple/dict second argument to execute().",
                                        "tool": "security_ast_scanner",
                                    }
                                )
            except SyntaxError:
                pass

    return findings


def run_security_analysis(files: list[SubmittedFile]) -> dict[str, Any]:
    """Run Bandit static analysis and deterministic AST/pattern vulnerability scanners."""
    bandit_findings, bandit_ok, bandit_err = _run_bandit(files)
    pattern_findings = _run_pattern_security_checks(files)
    combined = bandit_findings + pattern_findings

    return {
        "security_findings": combined,
        "bandit_executed": bandit_ok,
        "bandit_error": bandit_err,
        "total_issues": len(combined),
    }

