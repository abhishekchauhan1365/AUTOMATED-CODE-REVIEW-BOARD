"""End-to-end scenario tests for Clean, Vulnerable, and Mixed-quality code."""

from __future__ import annotations

import pytest

from orchestration.schemas import (
    AgentExecutionState,
    MergeDecision,
    SEVERITY_ORDER,
    SubmissionMetadata,
    SubmittedFile,
)
from orchestration.state import SharedChangeState
from orchestration.workflow import execute_review_workflow


@pytest.mark.asyncio
async def test_scenario_1_clean_code_approved():
    """Scenario 1: Clean code with corresponding unit tests -> APPROVE."""
    prod_code = (
        '"""Arithmetic utilities."""\n\n\n'
        "def calculate_discount(price: float, rate: float) -> float:\n"
        '    """Return discounted price given a rate in [0, 1]."""\n'
        "    if price < 0 or not 0 <= rate <= 1:\n"
        '        raise ValueError("Invalid price or rate")\n'
        "    return round(price * (1.0 - rate), 2)\n"
    )
    test_code = (
        '"""Tests for arithmetic utilities."""\n\n'
        "from billing import calculate_discount\n\n\n"
        "def test_calculate_discount():\n"
        '    """Verify discount math."""\n'
        "    assert calculate_discount(100.0, 0.2) == 80.0\n"
    )
    state = SharedChangeState(
        submission_metadata=SubmissionMetadata(title="Clean Feature PR", demo_mode=True),
        files=[
            SubmittedFile(path="billing.py", language="python", content=prod_code),
            SubmittedFile(path="test_billing.py", language="python", content=test_code),
        ],
    )

    result = await execute_review_workflow(state, demo_mode=True)
    assert result.data.overall_status == "completed"
    assert result.data.merge_recommendation is not None
    assert result.data.merge_recommendation.decision == MergeDecision.APPROVE
    for name in ("diff_agent", "style_agent", "security_agent", "test_coverage_agent", "reviewer_manager"):
        assert result.data.agent_statuses[name].status == AgentExecutionState.COMPLETED


@pytest.mark.asyncio
async def test_scenario_2_vulnerable_code_request_changes():
    """Scenario 2: Hardcoded secret + SQLi + missing tests -> REQUEST_CHANGES + validated patch."""
    vuln_diff = """diff --git a/auth_db.py b/auth_db.py
new file mode 100644
--- /dev/null
+++ b/auth_db.py
@@ -0,0 +1,11 @@
+import sqlite3
+
+GROQ_TOKEN = "gsk_1234567890abcdefghij123456"
+
+def get_user(conn, username):
+    cur = conn.cursor()
+    cur.execute(f"SELECT * FROM users WHERE name = '{username}'")
+    return cur.fetchone()
+
+def run_shell(cmd):
+    import subprocess
+    subprocess.run(cmd, shell=True)
"""
    state = SharedChangeState(
        submission_metadata=SubmissionMetadata(
            title="Vulnerable Auth Patch",
            submission_type="diff",
            demo_mode=True,
        ),
        files=[],
        git_diff=vuln_diff,
    )

    result = await execute_review_workflow(state, demo_mode=True)
    assert result.data.overall_status == "completed"
    assert result.data.merge_recommendation is not None
    assert result.data.merge_recommendation.decision == MergeDecision.REQUEST_CHANGES
    assert result.data.severity_summary["CRITICAL"] >= 1
    assert result.data.fix_suggestion is not None
    assert result.data.fix_suggestion.available is True
    assert result.data.fix_suggestion.validation_status == "valid"
    assert "--- a/auth_db.py" in result.data.fix_suggestion.proposed_patch
    assert "gsk_1234567890abcdefghij123456" not in result.data.fix_suggestion.proposed_patch


@pytest.mark.asyncio
async def test_scenario_3_mixed_quality_consolidation_and_ranking():
    """Scenario 3: Mixed-quality code -> deduplicated & strictly severity-ranked findings."""
    mixed_code = (
        "import json\n"
        "import os\n\n"
        "def FetchData(x, a, b, c, d):\n"
        "    if a > 0:\n"
        "        if b > 0:\n"
        "            if c > 0:\n"
        "                if d > 0:\n"
        "                    return eval(x)\n"
        "    return None\n"
    )
    state = SharedChangeState(
        submission_metadata=SubmissionMetadata(title="Mixed Quality PR", demo_mode=True),
        files=[SubmittedFile(path="loader.py", language="python", content=mixed_code)],
    )

    result = await execute_review_workflow(state, demo_mode=True)
    findings = result.data.consolidated_findings
    assert len(findings) >= 3

    # Verify strict descending severity ordering
    ranks = [SEVERITY_ORDER[f.severity] for f in findings]
    assert ranks == sorted(ranks, reverse=True)

    # Verify multiple agents contributed
    agents_present = {f.agent for f in findings}
    assert "security_agent" in agents_present
    assert "test_coverage_agent" in agents_present
    assert result.data.merge_recommendation is not None
    assert result.data.merge_recommendation.decision == MergeDecision.REQUEST_CHANGES

