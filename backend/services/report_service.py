"""Append-only JSONL execution logger for Automated Code Review Board."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Optional

from orchestration.schemas import ExecutionEvent
from services.file_service import redact_secrets_in_text

_LOG_LOCK = threading.Lock()
DEFAULT_LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "review_runs.jsonl"


def get_log_path() -> Path:
    """Resolve the append-only JSONL log file path from env or default."""
    env_path = os.getenv("RUN_LOG_PATH")
    if env_path:
        p = Path(env_path)
        if not p.is_absolute():
            p = Path(__file__).resolve().parent.parent / p
        return p
    return DEFAULT_LOG_PATH


def append_execution_event(event: ExecutionEvent, log_path: Optional[Path] = None) -> None:
    """Append a single structured ExecutionEvent line to review_runs.jsonl without overwriting."""
    target = log_path or get_log_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = event.model_dump()
    if payload.get("message"):
        payload["message"] = redact_secrets_in_text(str(payload["message"]))
    if payload.get("error"):
        payload["error"] = redact_secrets_in_text(str(payload["error"]))

    line = json.dumps(payload, ensure_ascii=False)
    with _LOG_LOCK:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()


def read_review_logs(review_id: Optional[str] = None, log_path: Optional[Path] = None) -> list[dict]:
    """Read logged JSONL execution records, optionally filtered by review_id."""
    target = log_path or get_log_path()
    if not target.exists():
        return []

    records: list[dict] = []
    with _LOG_LOCK:
        with open(target, "r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    if review_id is None or item.get("review_id") == review_id:
                        records.append(item)
                except json.JSONDecodeError:
                    continue
    return records

