"""Unit and integration tests for each of the six independent agents and their tools."""

from __future__ import annotations

import pytest

from agents.diff_agent import run_diff_agent
from agents.fix_suggestion_agent import run_fix_suggestion_agent
from agents.reviewer_manager import run_reviewer_manager
from agents.security_agent import run_security_agent
from agents.style_agent import run_style_agent
from agents.test_coverage_agent import run_test_coverage_agent
from orchestration.schemas import (
    AgentExecutionState,
    Finding,
    MergeDecision,
    Severity,
    SubmissionMetadata,
    SubmittedFile,
)
from orchestration.state import SharedChangeState


@pytest.mark.asyncio
async def test_all_six_agents_independently_and_two_tools_each():
    raw_secret = "sk-proj-TestSecretKey9876543210abcdef"
    vuln_code = (
        f'API_KEY = "{raw_secret}"\n'
        "def run_user_expr(user_input):\n"
        "    return eval(user_input)\n"
    )
    state = SharedChangeState(
        submission_metadata=SubmissionMetadata(title="Independent Agent Test", demo_mode=True),
        files=[SubmittedFile(path="service.py", language="python", content=vuln_code)],
    )

    # 1. Diff Agent
    diff_out = await run_diff_agent(state)
    assert "modified_files" in diff_out
    assert len(state.data.agent_statuses["diff_agent"].tools_invoked) >= 2
    assert state.data.agent_statuses["diff_agent"].status == AgentExecutionState.COMPLETED

    # 2. Style Agent
    style_out = await run_style_agent(state)
    assert "complexity_metrics" in style_out
    assert len(state.data.agent_statuses["style_agent"].tools_invoked) >= 2
    assert state.data.agent_statuses["style_agent"].status == AgentExecutionState.COMPLETED

    # 3. Security Agent
    sec_out = await run_security_agent(state)
    assert sec_out["secrets_count"] >= 1
    assert sec_out["vulnerabilities_count"] >= 1
    assert len(state.data.agent_statuses["security_agent"].tools_invoked) >= 2
    # Secret must never appear unredacted in any finding
    for f in state.data.agent_findings["security_agent"]:
        assert raw_secret not in f.evidence
        assert raw_secret not in f.description

    # 4. Test-Coverage Agent
    test_out = await run_test_coverage_agent(state)
    assert test_out["runtime_coverage_executed"] is False
    assert len(state.data.agent_statuses["test_coverage_agent"].tools_invoked) >= 2
    assert len(test_out["untested_functions"]) >= 1

    # 5. Reviewer Manager
    mgr_out = await run_reviewer_manager(state)
    assert mgr_out["decision"] == MergeDecision.REQUEST_CHANGES.value
    assert len(state.data.agent_statuses["reviewer_manager"].tools_invoked) >= 2
    assert len(state.data.consolidated_findings) >= 2

    # 6. Fix-Suggestion Agent
    fix_out = await run_fix_suggestion_agent(state)
    assert fix_out["available"] is True
    assert state.data.fix_suggestion is not None
    assert state.data.fix_suggestion.validation_status == "valid"
    assert state.data.fix_suggestion.requires_explicit_approval is True
    assert state.data.fix_suggestion.user_approved is False
    assert raw_secret not in state.data.fix_suggestion.proposed_patch
    assert len(state.data.agent_statuses["fix_suggestion_agent"].tools_invoked) >= 2


@pytest.mark.asyncio
async def test_reviewer_manager_handles_failed_specialist_gracefully():
    """Reviewer Manager must never report a failed agent as passed and must record failure."""
    state = SharedChangeState(
        submission_metadata=SubmissionMetadata(title="Failure Handling Test", demo_mode=True),
        files=[SubmittedFile(path="clean.py", language="python", content="def add(a: int, b: int) -> int:\n    return a + b\n")],
    )
    await state.mark_agent_running("security_agent", "Scanning")
    await state.mark_agent_failed("security_agent", "Simulated scanner crash")
    await run_diff_agent(state)
    await run_style_agent(state)
    await run_test_coverage_agent(state)

    await run_reviewer_manager(state)
    rec = state.data.merge_recommendation
    assert rec is not None
    assert rec.has_agent_failures is True
    assert rec.decision == MergeDecision.REQUEST_CHANGES
    assert "Security Agent" in " ".join(rec.decision_factors)
    assert state.data.agent_statuses["security_agent"].status == AgentExecutionState.FAILED

