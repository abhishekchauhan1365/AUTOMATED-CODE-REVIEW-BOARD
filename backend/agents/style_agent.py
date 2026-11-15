"""Agent 2: Style Agent — runs Ruff linting, complexity analysis, and duplication detection."""

from __future__ import annotations

import json
from typing import Annotated, Any, Optional
from uuid import uuid4

from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.functions import kernel_function

from agents.base import StateAwareSKAgent
from orchestration.schemas import Finding, Severity, SubmittedFile
from orchestration.state import SharedChangeState
from services.llm_service import LLMServiceError, create_kernel, invoke_sk_agent_json
from tools.complexity_analyzer import calculate_complexity
from tools.style_checker import run_linter


STYLE_AGENT_INSTRUCTIONS = """You are the Style Agent on an Automated Code Review Board.
Interpret the deterministic linter (Ruff), cyclomatic complexity (Radon), and duplication tool outputs in TOOL_EVIDENCE_JSON.
Return strictly a JSON object with keys:
- "summary": concise 1-2 sentence overview of code style, readability, and maintainability.
- "contextual_notes": list of up to 3 actionable readability suggestions grounded in the tool data.
- "additional_findings": list of additional style findings ONLY if clearly supported by the metrics (otherwise empty list).
Do NOT fabricate lint issues."""


class StyleAgentPlugin:
    """Semantic Kernel plugin exposing Style Agent's two real Python tools."""

    def __init__(self, files: list[SubmittedFile]) -> None:
        self._files = files

    @kernel_function(
        name="run_linter_tool",
        description="Run Ruff linter and structural style checks across submitted source files.",
    )
    def run_linter_tool(
        self,
        scope: Annotated[str, "Lint scope"] = "all",
    ) -> Annotated[str, "JSON linting results"]:
        return json.dumps(run_linter(self._files), default=str)

    @kernel_function(
        name="calculate_complexity_tool",
        description="Calculate cyclomatic complexity and detect duplicated code blocks.",
    )
    def calculate_complexity_tool(
        self,
        scope: Annotated[str, "Complexity scope"] = "all",
    ) -> Annotated[str, "JSON complexity and duplication metrics"]:
        return json.dumps(calculate_complexity(self._files), default=str)


def build_style_sk_agent(state: SharedChangeState, kernel: Kernel) -> StateAwareSKAgent:
    """Create Semantic Kernel Agent instance for ConcurrentOrchestration."""
    return StateAwareSKAgent(
        name="style_agent",
        description="Analyzes formatting, linting (Ruff), cyclomatic complexity, and duplication.",
        kernel=kernel,
        state=state,
        runner=run_style_agent,
    )


async def run_style_agent(
    state: SharedChangeState,
    kernel: Optional[Kernel] = None,
) -> dict[str, Any]:
    """Independently callable entrypoint for the Style Agent."""
    agent_name = "style_agent"
    await state.mark_agent_running(agent_name, "Running Ruff linter and style checks...")

    try:
        active_kernel = kernel
        is_demo = state.data.submission_metadata.demo_mode
        if active_kernel is None:
            active_kernel, is_demo, _ = create_kernel(demo_mode=is_demo)

        plugin = StyleAgentPlugin(files=state.data.files)
        plugin_name = f"style_tools_{uuid4().hex[:8]}"
        active_kernel.add_plugin(plugin, plugin_name=plugin_name)

        # Tool 1: run_linter via SK KernelFunction
        await state.update_agent_activity(agent_name, "Invoking Ruff & structural linter", "run_linter")
        lint_res = await active_kernel.invoke(plugin_name=plugin_name, function_name="run_linter_tool")
        lint_data = json.loads(str(lint_res))

        # Tool 2: calculate_complexity via SK KernelFunction
        await state.update_agent_activity(agent_name, "Invoking complexity & duplication analyzer", "calculate_complexity")
        comp_res = await active_kernel.invoke(plugin_name=plugin_name, function_name="calculate_complexity_tool")
        comp_data = json.loads(str(comp_res))

        findings: list[Finding] = []
        for item in lint_data.get("issues", []):
            sev_str = str(item.get("severity", "LOW")).upper()
            sev = Severity[sev_str] if sev_str in Severity.__members__ else Severity.LOW
            findings.append(
                Finding(
                    id=f"style-lint-{uuid4().hex[:6]}",
                    title=str(item.get("title", "Style issue")),
                    description=str(item.get("description", "")),
                    severity=sev,
                    agent=agent_name,
                    category="style",
                    file_path=str(item.get("file_path", "unknown")),
                    line_start=item.get("line_start"),
                    line_end=item.get("line_end"),
                    evidence=f"Rule {item.get('rule_id', 'STYLE')} ({item.get('tool', 'linter')})",
                    recommended_action=f"Resolve {item.get('rule_id', 'style')} issue to improve code clarity.",
                    rule_id=str(item.get("rule_id")) if item.get("rule_id") else None,
                    source="deterministic_tool",
                    confidence=0.95,
                )
            )

        for item in comp_data.get("complexity_issues", []):
            sev_str = str(item.get("severity", "MEDIUM")).upper()
            sev = Severity[sev_str] if sev_str in Severity.__members__ else Severity.MEDIUM
            findings.append(
                Finding(
                    id=f"style-cc-{uuid4().hex[:6]}",
                    title=str(item.get("title", "High cyclomatic complexity")),
                    description=str(item.get("description", "")),
                    severity=sev,
                    agent=agent_name,
                    category="style",
                    file_path=str(item.get("file_path", "unknown")),
                    line_start=item.get("line_start"),
                    line_end=item.get("line_end"),
                    evidence=f"Complexity threshold exceeded ({item.get('rule_id')})",
                    recommended_action="Refactor complex control flow into smaller, well-named helper functions.",
                    rule_id=item.get("rule_id"),
                    source="deterministic_tool",
                    confidence=0.92,
                )
            )

        for item in comp_data.get("duplication_issues", []):
            findings.append(
                Finding(
                    id=f"style-dup-{uuid4().hex[:6]}",
                    title=str(item.get("title", "Code duplication detected")),
                    description=str(item.get("description", "")),
                    severity=Severity.LOW,
                    agent=agent_name,
                    category="style",
                    file_path=str(item.get("file_path", "unknown")),
                    line_start=item.get("line_start"),
                    line_end=item.get("line_end"),
                    evidence=str(item.get("evidence", ""))[:160],
                    recommended_action="Extract the duplicated block into a shared reusable function.",
                    rule_id=item.get("rule_id"),
                    source="deterministic_tool",
                    confidence=0.9,
                )
            )

        await state.update_agent_activity(agent_name, "Synthesizing readability guidance with Semantic Kernel agent...")
        sk_chat = ChatCompletionAgent(
            kernel=active_kernel,
            name="StyleAgent",
            instructions=STYLE_AGENT_INSTRUCTIONS,
        )
        evidence_ctx = {
            "lint_issues": lint_data.get("issues", [])[:20],
            "complexity_issues": comp_data.get("complexity_issues", [])[:10],
            "duplication_issues": comp_data.get("duplication_issues", [])[:10],
            "ruff_executed": lint_data.get("ruff_executed", False),
        }
        prompt = (
            "Review the deterministic style, lint, complexity, and duplication outputs below.\n"
            f"TOOL_EVIDENCE_JSON:\n{json.dumps(evidence_ctx, indent=2)}"
        )

        summary = (
            f"Detected {len(findings)} style/complexity finding(s) "
            f"(Ruff executed: {lint_data.get('ruff_executed', False)})."
        )
        contextual_notes: list[str] = []
        try:
            llm_data = await invoke_sk_agent_json(sk_chat, prompt)
            if llm_data.get("summary"):
                summary = str(llm_data["summary"])
            contextual_notes = [str(n) for n in llm_data.get("contextual_notes", []) if n]
        except LLMServiceError as llm_exc:
            summary += f" (LLM note unavailable: {llm_exc})"

        output_data = {
            "summary": summary,
            "contextual_notes": contextual_notes,
            "ruff_executed": lint_data.get("ruff_executed", False),
            "ruff_error": lint_data.get("ruff_error"),
            "complexity_metrics": comp_data.get("metrics", []),
            "total_findings": len(findings),
        }
        await state.mark_agent_completed(
            agent_name=agent_name,
            findings=findings,
            output_data=output_data,
            summary=summary,
            tools_invoked=["run_linter", "calculate_complexity"],
        )
        return output_data

    except Exception as exc:
        await state.mark_agent_failed(agent_name, str(exc))
        return {"error": str(exc)}

