"""Secret and credential static scanner tool with automatic redaction."""

from __future__ import annotations

import math
import re
from typing import Any

from orchestration.schemas import SubmittedFile
from services.file_service import redact_secret, redact_secrets_in_text


_SECRET_PATTERNS: list[tuple[str, str, re.Pattern[str], str]] = [
    ("SEC-KEY-GROQ", "Hardcoded Groq API Key", re.compile(r"\b(gsk_[A-Za-z0-9]{16,})\b"), "CRITICAL"),
    ("SEC-KEY-OPENAI", "Hardcoded OpenAI / Bearer API Key", re.compile(r"\b(sk-[A-Za-z0-9\-_]{20,})\b"), "CRITICAL"),
    ("SEC-KEY-AWS", "Hardcoded AWS Access Key ID", re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), "CRITICAL"),
    ("SEC-KEY-GITHUB", "Hardcoded GitHub Personal Access Token", re.compile(r"\b(ghp_[A-Za-z0-9]{24,})\b"), "CRITICAL"),
    ("SEC-KEY-GOOGLE", "Hardcoded Google API Key", re.compile(r"\b(AIza[0-9A-Za-z\-_]{30,})\b"), "CRITICAL"),
    ("SEC-KEY-SLACK", "Hardcoded Slack Token", re.compile(r"\b(xox[baprs]-[0-9A-Za-z\-]{12,})\b"), "CRITICAL"),
    (
        "SEC-PRIVATE-KEY",
        "Embedded Private Key Material",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
        "CRITICAL",
    ),
    (
        "SEC-CRED-ASSIGN",
        "Hardcoded Password / Secret / Token Assignment",
        re.compile(
            r"""(?i)\b(password|passwd|pwd|secret|secret_key|api_key|apikey|access_token|auth_token|db_pass|jwt_secret)\b\s*[:=]\s*['"]([^'"]{4,})['"]"""
        ),
        "CRITICAL",
    ),
    (
        "SEC-CONN-STR",
        "Database Connection String with Embedded Credentials",
        re.compile(r"""(?i)(postgres|postgresql|mysql|mongodb(?:\+srv)?|redis)://[^:\s'"]+:[^@\s'"]+@[^\s'"]+"""),
        "HIGH",
    ),
]

_PLACEHOLDER_VALUES = {
    "changeme",
    "your_api_key",
    "your_groq_api_key_here",
    "example",
    "placeholder",
    "dummy",
    "test",
    "none",
    "null",
    "os.environ",
}


def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    freq: dict[str, int] = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    length = len(text)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


def scan_for_secrets(files: list[SubmittedFile]) -> dict[str, Any]:
    """Scan submitted files for hardcoded API keys, passwords, tokens, and private keys."""
    findings: list[dict[str, Any]] = []
    seen_locations: set[tuple[str, int, str]] = set()

    for sf in files:
        if sf.status == "deleted" or not sf.content.strip():
            continue
        if sf.path.endswith((".env.example", ".md")):
            continue

        for line_no, raw_line in enumerate(sf.content.splitlines(), start=1):
            stripped = raw_line.strip()
            if not stripped or stripped.startswith(("#", "//", "/*")):
                continue
            # Ignore safe environment variable lookups
            if "os.getenv(" in raw_line or "os.environ" in raw_line or "process.env." in raw_line:
                continue

            for rule_id, title, pattern, severity in _SECRET_PATTERNS:
                m = pattern.search(raw_line)
                if not m:
                    continue

                if rule_id == "SEC-CRED-ASSIGN":
                    candidate_val = m.group(2).strip()
                    lower_val = candidate_val.lower()
                    if lower_val in _PLACEHOLDER_VALUES or lower_val.startswith(("your_", "<", "${", "{{", "test_")):
                        continue
                    masked_evidence = redact_secrets_in_text(stripped)
                else:
                    matched_token = m.group(0)
                    masked_evidence = stripped.replace(matched_token, redact_secret(matched_token))

                key = (sf.path, line_no, rule_id)
                if key in seen_locations:
                    continue
                seen_locations.add(key)

                findings.append(
                    {
                        "rule_id": rule_id,
                        "title": title,
                        "description": (
                            f"Potential hardcoded credential or secret detected in {sf.path} at line {line_no}. "
                            "Sensitive value has been redacted in evidence."
                        ),
                        "severity": severity,
                        "file_path": sf.path,
                        "line_start": line_no,
                        "line_end": line_no,
                        "evidence": masked_evidence[:180],
                        "recommended_action": (
                            "Remove hardcoded credentials from source code and load them securely "
                            "from environment variables or a secrets manager."
                        ),
                    }
                )

            # High-entropy string check on long quoted tokens if not already flagged
            if not any(loc[0] == sf.path and loc[1] == line_no for loc in seen_locations):
                for qm in re.finditer(r"""['"]([A-Za-z0-9+/=_\-]{28,})['"]""", raw_line):
                    token = qm.group(1)
                    if " " not in token and "/" not in token[:5] and _shannon_entropy(token) >= 4.2:
                        if re.search(r"(key|token|secret|auth|bearer|cred)", raw_line, re.I):
                            seen_locations.add((sf.path, line_no, "SEC-ENTROPY"))
                            findings.append(
                                {
                                    "rule_id": "SEC-ENTROPY",
                                    "title": "High-entropy credential-like string literal",
                                    "description": (
                                        f"High-entropy literal associated with a credential identifier "
                                        f"at {sf.path}:{line_no}."
                                    ),
                                    "severity": "HIGH",
                                    "file_path": sf.path,
                                    "line_start": line_no,
                                    "line_end": line_no,
                                    "evidence": stripped.replace(token, redact_secret(token))[:180],
                                    "recommended_action": "Move secret literals to environment variables.",
                                }
                            )
                            break

    return {
        "secret_findings": findings,
        "total_secrets_detected": len(findings),
    }

