"""Agent 5: Reviewer Manager — orchestrates Fan-Out/Fan-In, deduplicates, ranks, and decides."""

from __future__ import annotations

import json
from typing import Annotated, Any, Optional
from uuid import uuid4

from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.functions import kernel_function

from orchestration.schemas import AgentExecutionState, Finding, MergeDecision
from orchestration.state import SharedChangeState
from services.llm_service import LLMServiceError, create_kernel, invoke_sk_agent_json
from tools.deduplicator import deduplicate_findings
from tools.finding_ranker import generate_review_report, rank_findings


REVIEWER_MANAGER_INSTRUCTIONS = """You are the Reviewer Manager leading an Automated Code Review Board.
You have collected findings from Diff, Style, Security, and Test-Coverage agents and run deduplication + severity ranking.
Given TOOL_EVIDENCE_JSON, return strictly a JSON object with keys:
- "decision": either "APPROVE" or "REQUEST_CHANGES".
- "reasoning": clear 2-4 sentence justification citing the exact finding counts, severity breakdown, any agent failures, and why the decision is appropriate.
Rules:
- Any CRITICAL finding or HIGH-severity security issue MUST result in REQUEST_CHANGES.
- Never claim a check passed if that agent failed or was not executed."""


class ReviewerManagerPlugin:
    """Semantic Kernel plugin exposing Reviewer Manager's two real Python tools."""

    def __init__(self, findings: list[Finding], state: SharedChangeState) -> None:
        self._findings = findings
        self._state = state
        self._deduped: list[Finding] = []
        self._dedup_stats: dict[str, Any] = {}

    @kernel_function(
        name="deduplicate_findings_tool",
        description="Deduplicate overlapping findings across specialist agents.",
    )
    def deduplicate_findings_tool(
        self,
        scope: Annotated[str, "Deduplication scope"] = "all",
    ) -> Annotated[str, "JSON deduplication stats"]:
        res = deduplicate_findings(self._findings)
        self._deduped = res["deduplicated_findings"]
        self._dedup_stats = {
            "original_count": res["original_count"],
            "deduplicated_count": res["deduplicated_count"],
            "duplicates_removed": res["duplicates_removed"],
        }
        return json.dumps(self._dedup_stats)

    @kernel_function(
        name="generate_review_report_tool",
        description="Rank deduplicated findings by severity and generate merge recommendation.",
    )
    def generate_review_report_tool(
        self,
        scope: Annotated[str, "Report scope"] = "all",
    ) -> Annotated[str, "JSON ranked report summary"]:
        ranked = rank_findings(self._deduped or self._findings)
        report = generate_review_report(ranked, self._state.data.agent_statuses)
        return json.dumps(
            {
                "ranked_count": len(ranked),
                "severity_summary": report["severity_summary"],
                "decision": report["merge_recommendation"].decision.value,
                "decision_factors": report["merge_recommendation"].decision_factors,
                "blocking_findings_count": report["merge_recommendation"].blocking_findings_count,
            }
        )


async def run_reviewer_manager(
    state: SharedChangeState,
    kernel: Optional[Kernel] = None,
) -> dict[str, Any]:
    """Consolidate specialist findings via fan-in, deduplicate, rank, and issue merge decision."""
    agent_name = "reviewer_manager"
    await state.mark_agent_running(agent_name, "Collecting and validating specialist agent outputs...")

    try:
        active_kernel = kernel
        is_demo = state.data.submission_metadata.demo_mode
        if active_kernel is None:
            active_kernel, is_demo, _ = create_kernel(demo_mode=is_demo)

        # Collect all specialist findings from SharedChangeState
        specialist_names = ("diff_agent", "style_agent", "security_agent", "test_coverage_agent")
        all_findings: list[Finding] = []
        failed_specialists: list[str] = []

        for sp in specialist_names:
            rec = state.data.agent_statuses.get(sp)
            if rec and rec.status == AgentExecutionState.FAILED:
                failed_specialists.append(rec.display_name)
            all_findings.extend(state.data.agent_findings.get(sp, []))

        plugin = ReviewerManagerPlugin(findings=all_findings, state=state)
        plugin_name = f"manager_tools_{uuid4().hex[:8]}"
        active_kernel.add_plugin(plugin, plugin_name=plugin_name)

        # Tool 1: deduplicate_findings via SK KernelFunction
        await state.update_agent_activity(agent_name, "Deduplicating overlapping findings", "deduplicate_findings")
        dedup_json = json.loads(
            str(await active_kernel.invoke(plugin_name=plugin_name, function_name="deduplicate_findings_tool"))
        )
        deduped = plugin._deduped

        # Tool 2: rank_findings + generate_review_report via SK KernelFunction
        await state.update_agent_activity(agent_name, "Ranking findings and evaluating merge rules", "generate_review_report")
        _ = await active_kernel.invoke(plugin_name=plugin_name, function_name="generate_review_report_tool")
        ranked = rank_findings(deduped)
        deterministic_report = generate_review_report(ranked, state.data.agent_statuses)
        det_rec = deterministic_report["merge_recommendation"]
        sev_summary = deterministic_report["severity_summary"]

        # Invoke Semantic Kernel ChatCompletionAgent for final executive reasoning
        await state.update_agent_activity(agent_name, "Synthesizing merge decision justification...")
        sk_chat = ChatCompletionAgent(
            kernel=active_kernel,
            name="ReviewerManager",
            instructions=REVIEWER_MANAGER_INSTRUCTIONS,
        )
        evidence_ctx = {
            "total_raw_findings": dedup_json["original_count"],
            "total_consolidated": len(ranked),
            "duplicates_removed": dedup_json["duplicates_removed"],
            "severity_summary": sev_summary,
            "recommended_decision": det_rec.decision.value,
            "blocking_count": det_rec.blocking_findings_count,
            "decision_factors": det_rec.decision_factors,
            "failed_agents": failed_specialists,
            "top_findings": [
                {
                    "title": f.title,
                    "severity": f.severity.value,
                    "agent": f.agent,
                    "file_path": f.file_path,
                    "line_start": f.line_start,
                }
                for f in ranked[:10]
            ],
        }
        prompt = (
            "Generate the final merge recommendation reasoning based strictly on these consolidated findings.\n"
            f"TOOL_EVIDENCE_JSON:\n{json.dumps(evidence_ctx, indent=2)}"
        )

        llm_reasoning: Optional[str] = None
        try:
            llm_data = await invoke_sk_agent_json(sk_chat, prompt)
            llm_reasoning = llm_data.get("reasoning")
        except LLMServiceError:
            llm_reasoning = None

        # Enforce deterministic safety guardrail while incorporating LLM reasoning
        final_report = generate_review_report(ranked, state.data.agent_statuses, llm_reasoning=llm_reasoning)
        final_rec = final_report["merge_recommendation"]

        await state.set_consolidated_review(
            consolidated_findings=ranked,
            severity_summary=sev_summary,
            merge_recommendation=final_rec,
        )

        summary = (
            f"Recommendation: {final_rec.decision.value}. Consolidated {len(ranked)} unique finding(s) "
            f"(removed {dedup_json['duplicates_removed']} duplicate(s))."
        )
        output_data = {
            "decision": final_rec.decision.value,
            "reasoning": final_rec.reasoning,
            "decision_factors": final_rec.decision_factors,
            "severity_summary": sev_summary,
            "total_raw_findings": dedup_json["original_count"],
            "total_consolidated_findings": len(ranked),
            "duplicates_removed": dedup_json["duplicates_removed"],
            "failed_agents": failed_specialists,
        }
        await state.mark_agent_completed(
            agent_name=agent_name,
            findings=[],
            output_data=output_data,
            summary=summary,
            tools_invoked=["deduplicate_findings", "generate_review_report"],
        )
        return output_data

    except Exception as exc:
        await state.mark_agent_failed(agent_name, str(exc))
        return {"error": str(exc)}

