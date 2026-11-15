"""Severity ranking and consolidated review report generation tool."""

from __future__ import annotations

from typing import Any

from orchestration.schemas import (
    AgentExecutionState,
    AgentStatusRecord,
    Finding,
    MergeDecision,
    MergeRecommendation,
    SEVERITY_ORDER,
    Severity,
)


def rank_findings(findings: list[Finding]) -> list[Finding]:
    """Rank findings deterministically by severity, security impact, and confidence."""
    category_priority = {"security": 4, "correctness": 3, "testing": 2, "style": 1, "general": 0}
    return sorted(
        findings,
        key=lambda f: (
            -SEVERITY_ORDER[f.severity],
            -category_priority.get(f.category.lower(), 0),
            -f.confidence,
            f.file_path,
            f.line_start or 0,
        ),
    )


def generate_review_report(
    ranked_findings: list[Finding],
    agent_statuses: dict[str, AgentStatusRecord],
    llm_reasoning: str | None = None,
) -> dict[str, Any]:
    """Evaluate decision rules and produce severity summary + MergeRecommendation."""
    severity_summary: dict[str, int] = {
        Severity.CRITICAL.value: 0,
        Severity.HIGH.value: 0,
        Severity.MEDIUM.value: 0,
        Severity.LOW.value: 0,
        Severity.INFO.value: 0,
    }
    for f in ranked_findings:
        severity_summary[f.severity.value] = severity_summary.get(f.severity.value, 0) + 1

    critical_count = severity_summary[Severity.CRITICAL.value]
    high_security_count = sum(
        1 for f in ranked_findings if f.severity == Severity.HIGH and f.category.lower() == "security"
    )
    high_total = severity_summary[Severity.HIGH.value]
    medium_total = severity_summary[Severity.MEDIUM.value]

    failed_agents = [
        rec.display_name
        for name, rec in agent_statuses.items()
        if name not in ("reviewer_manager", "fix_suggestion_agent")
        and rec.status == AgentExecutionState.FAILED
    ]

    decision_factors: list[str] = []
    blocking_count = critical_count + high_security_count

    if critical_count > 0:
        decision = MergeDecision.REQUEST_CHANGES
        decision_factors.append(f"{critical_count} CRITICAL finding(s) detected that block merge.")
    elif high_security_count > 0:
        decision = MergeDecision.REQUEST_CHANGES
        decision_factors.append(f"{high_security_count} HIGH-severity security finding(s) require remediation.")
    elif high_total >= 2:
        decision = MergeDecision.REQUEST_CHANGES
        blocking_count += high_total
        decision_factors.append(f"{high_total} HIGH-severity findings exceed merge threshold.")
    elif "Security Agent" in failed_agents:
        decision = MergeDecision.REQUEST_CHANGES
        decision_factors.append("Security Agent failed to complete; cannot safely approve without security scan.")
    else:
        decision = MergeDecision.APPROVE
        if high_total == 1:
            decision_factors.append("One non-security HIGH finding noted for follow-up; no critical blockers.")
        elif medium_total > 0 or severity_summary[Severity.LOW.value] > 0:
            decision_factors.append(
                f"No critical or high-severity security blockers ({medium_total} medium, "
                f"{severity_summary[Severity.LOW.value]} low advisories)."
            )
        else:
            decision_factors.append("All specialist checks passed with zero blocking issues.")

    if failed_agents:
        decision_factors.append(
            f"Incomplete checks: {', '.join(failed_agents)} failed and must not be treated as passed."
        )

    default_reasoning = (
        f"Merge recommendation is {decision.value}. "
        + " ".join(decision_factors)
    )
    final_reasoning = llm_reasoning.strip() if llm_reasoning and llm_reasoning.strip() else default_reasoning

    recommendation = MergeRecommendation(
        decision=decision,
        reasoning=final_reasoning,
        decision_factors=decision_factors,
        blocking_findings_count=blocking_count,
        has_agent_failures=len(failed_agents) > 0,
    )

    return {
        "severity_summary": severity_summary,
        "merge_recommendation": recommendation,
    }

