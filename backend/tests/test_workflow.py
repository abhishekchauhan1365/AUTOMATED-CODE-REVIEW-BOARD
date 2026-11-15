"""API, persistence, safety, and append-only JSONL logging tests."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from services.file_service import FileValidationError, sanitize_relative_path


def test_path_traversal_rejected():
    try:
        sanitize_relative_path("../../etc/passwd")
        assert False, "Expected FileValidationError"
    except FileValidationError:
        pass


def test_full_api_lifecycle_and_append_only_logs(tmp_path: Path, monkeypatch):
    log_file = tmp_path / "review_runs.jsonl"
    monkeypatch.setenv("RUN_LOG_PATH", str(log_file))
    monkeypatch.setenv("USE_MOCK_LLM", "true")

    with TestClient(app) as client:
        # Submit a vulnerable diff
        resp = client.post(
            "/api/reviews",
            json={
                "title": "API Integration Review",
                "description": "Checks end-to-end API + SQLite + JSONL",
                "submission_type": "diff",
                "demo_mode": True,
                "git_diff": (
                    "diff --git a/utils.py b/utils.py\n"
                    "--- a/utils.py\n"
                    "+++ b/utils.py\n"
                    "@@ -1,2 +1,3 @@\n"
                    "+import hashlib\n"
                    "+def hash_pw(pw):\n"
                    "+    return hashlib.md5(pw.encode()).hexdigest()\n"
                ),
            },
        )
        assert resp.status_code == 202
        review_id = resp.json()["review_id"]

        # Poll status until completed (runs fast in demo mode)
        deadline = time.time() + 15
        status_data = None
        while time.time() < deadline:
            st = client.get(f"/api/reviews/{review_id}/status")
            assert st.status_code == 200
            status_data = st.json()
            if status_data["overall_status"] in ("completed", "failed"):
                break
            time.sleep(0.15)

        assert status_data is not None
        assert status_data["overall_status"] == "completed"

        # Fetch full detail, findings, logs, and history
        detail = client.get(f"/api/reviews/{review_id}")
        assert detail.status_code == 200
        assert detail.json()["merge_recommendation"]["decision"] in ("APPROVE", "REQUEST_CHANGES")

        findings = client.get(f"/api/reviews/{review_id}/findings")
        assert findings.status_code == 200
        assert findings.json()["total"] >= 1

        # Patch safety: download MUST fail with 403 before explicit user approval
        dl_before = client.get(f"/api/reviews/{review_id}/patch/download")
        assert dl_before.status_code == 403

        approve = client.post(f"/api/reviews/{review_id}/patch/approve")
        assert approve.status_code == 200
        assert approve.json()["user_approved"] is True

        dl_after = client.get(f"/api/reviews/{review_id}/patch/download")
        assert dl_after.status_code == 200
        assert "--- a/utils.py" in dl_after.text

        # Verify append-only JSONL log recorded events
        logs_resp = client.get(f"/api/reviews/{review_id}/logs")
        assert logs_resp.status_code == 200
        assert len(logs_resp.json()["events"]) >= 6
        assert log_file.exists()
        first_count = len(log_file.read_text(encoding="utf-8").splitlines())

        # Second review appends rather than overwriting
        resp2 = client.post(
            "/api/reviews",
            json={
                "title": "Second Append Check",
                "submission_type": "files",
                "demo_mode": True,
                "files": [{"path": "ok.py", "content": "def ok():\n    return True\n"}],
            },
        )
        assert resp2.status_code == 202
        review_id_2 = resp2.json()["review_id"]
        deadline2 = time.time() + 15
        while time.time() < deadline2:
            if client.get(f"/api/reviews/{review_id_2}/status").json()["overall_status"] in ("completed", "failed"):
                break
            time.sleep(0.15)

        second_count = len(log_file.read_text(encoding="utf-8").splitlines())
        assert second_count > first_count
        # Confirm every line is valid JSON
        for line in log_file.read_text(encoding="utf-8").splitlines():
            json.loads(line)

        # Verify history & delete
        hist = client.get("/api/reviews")
        assert hist.status_code == 200
        ids = {item["review_id"] for item in hist.json()}
        assert review_id in ids and review_id_2 in ids

        del_resp = client.delete(f"/api/reviews/{review_id}")
        assert del_resp.status_code == 200
        client.delete(f"/api/reviews/{review_id_2}")

