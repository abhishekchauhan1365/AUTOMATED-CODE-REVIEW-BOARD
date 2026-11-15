"""Safe file ingestion, validation, path sanitization, and secret redaction."""

from __future__ import annotations

import os
import re
from pathlib import PurePosixPath
from typing import Iterable

from orchestration.schemas import SubmittedFile

ALLOWED_EXTENSIONS: set[str] = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".go",
    ".h",
    ".hpp",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
}

LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".go": "go",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
}

MAX_UPLOAD_FILES: int = int(os.getenv("MAX_UPLOAD_FILES", "25"))
MAX_FILE_SIZE_BYTES: int = int(os.getenv("MAX_FILE_SIZE_BYTES", str(512 * 1024)))
MAX_DIFF_SIZE_BYTES: int = 2 * 1024 * 1024


class FileValidationError(ValueError):
    """Raised when an uploaded file or path fails safety checks."""


def sanitize_relative_path(raw_path: str) -> str:
    """Sanitize a file path to prevent path traversal or unsafe file access."""
    if not raw_path or "\x00" in raw_path:
        raise FileValidationError("Invalid empty or null-byte file path.")

    normalized = raw_path.replace("\\", "/").strip()
    if normalized.startswith("/") or re.match(r"^[a-zA-Z]:", normalized):
        # Strip leading root/drive only if someone passed an IDE path, or reject traversal
        normalized = re.sub(r"^[a-zA-Z]:/+", "", normalized).lstrip("/")

    parts = [p for p in PurePosixPath(normalized).parts if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        raise FileValidationError(f"Unsafe path traversal detected in '{raw_path}'.")

    clean = "/".join(parts)
    if len(clean) > 260:
        raise FileValidationError(f"File path too long: '{clean[:40]}...'")
    return clean


def detect_language(file_path: str) -> str:
    """Return normalized language identifier for a file path."""
    suffix = PurePosixPath(file_path).suffix.lower()
    return LANGUAGE_MAP.get(suffix, "text")


def validate_extension(file_path: str) -> str:
    """Validate that the file extension is within the accepted allowlist."""
    suffix = PurePosixPath(file_path).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"Unsupported file extension '{suffix or '<none>'}' for '{file_path}'. "
            f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return suffix


def validate_and_build_submitted_files(raw_files: Iterable[dict]) -> list[SubmittedFile]:
    """Validate incoming file dictionaries and produce sanitized SubmittedFile models."""
    raw_list = list(raw_files)
    if not raw_list:
        raise FileValidationError("No source files provided.")
    if len(raw_list) > MAX_UPLOAD_FILES:
        raise FileValidationError(f"Too many files ({len(raw_list)}). Maximum allowed is {MAX_UPLOAD_FILES}.")

    validated: list[SubmittedFile] = []
    seen_paths: set[str] = set()

    for item in raw_list:
        raw_path = str(item.get("path") or item.get("name") or item.get("filename") or "").strip()
        clean_path = sanitize_relative_path(raw_path)
        validate_extension(clean_path)

        content = item.get("content", "")
        if not isinstance(content, str):
            raise FileValidationError(f"Content for '{clean_path}' must be UTF-8 text.")

        size_bytes = len(content.encode("utf-8"))
        if size_bytes > MAX_FILE_SIZE_BYTES:
            raise FileValidationError(
                f"File '{clean_path}' exceeds maximum size ({size_bytes} > {MAX_FILE_SIZE_BYTES} bytes)."
            )

        if clean_path in seen_paths:
            raise FileValidationError(f"Duplicate file path '{clean_path}' in submission.")
        seen_paths.add(clean_path)

        status = item.get("status", "modified")
        if status not in ("added", "modified", "deleted"):
            status = "modified"

        validated.append(
            SubmittedFile(
                path=clean_path,
                language=detect_language(clean_path),
                content=content,
                size_bytes=size_bytes,
                status=status,
            )
        )

    return validated


def redact_secret(value: str) -> str:
    """Mask sensitive credential values so raw secrets are never shown in reports or logs."""
    cleaned = value.strip()
    if len(cleaned) <= 6:
        return "***REDACTED***"
    return f"{cleaned[:3]}{'*' * min(12, max(4, len(cleaned) - 6))}{cleaned[-3:]}"


def redact_secrets_in_text(text: str) -> str:
    """Redact common API key / token / password patterns in free-form strings."""
    if not text:
        return text

    patterns = [
        r"(gsk_[A-Za-z0-9]{12,})",
        r"(sk-[A-Za-z0-9\-_]{16,})",
        r"(ghp_[A-Za-z0-9]{20,})",
        r"(AKIA[0-9A-Z]{16})",
        r"(AIza[0-9A-Za-z\-_]{25,})",
        r"(xox[baprs]-[0-9A-Za-z\-]{10,})",
    ]
    masked = text
    for pat in patterns:
        masked = re.sub(pat, lambda m: redact_secret(m.group(1)), masked)

    # Mask quoted secrets in key=value assignments
    masked = re.sub(
        r"(?i)\b(password|passwd|secret|api_key|apikey|token|private_key|auth_token)\b(\s*[:=]\s*['\"])([^'\"]{4,})(['\"])",
        lambda m: f"{m.group(1)}{m.group(2)}{redact_secret(m.group(3))}{m.group(4)}",
        masked,
    )
    return masked

