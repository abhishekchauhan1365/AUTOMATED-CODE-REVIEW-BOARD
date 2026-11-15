"""Agent 4: Test-Coverage Agent — discovers test mappings and missing test scenarios."""

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
from tools.coverage_analyzer import analyze_test_coverage
from tools.test_discovery import discover_test_files


TEST_COVERAGE_INSTRUCTIONS = """You are the Test-Coverage Agent on an Automated Code Review Board.
Analyze the test discovery and coverage analysis data in TOOL_EVIDENCE_JSON.
IMPORTANT: Never claim exact runtime line coverage unless runtime_coverage_executed is true.
Return strictly a JSON object with keys:
- "summary": concise 1-2 sentence test adequacy assessment.
- "missing_scenarios": list of specific test scenarios recommended for the changed functions.
- "additional_findings": list of additional testing gap findings if warranted (otherwise empty list)."""


class TestCoverageAgentPlugin:
    """Semantic Kernel plugin exposing Test-Coverage Agent's two real Python tools."""

    def __init__(self, files: list[SubmittedFile]) -> None:
        self._files = files
        self._last_discovery: dict[str, Any] = {}

    @kernel_function(
        name="discover_test_files_tool",
        description="Discover test files, test cases, and map production functions to test references.",
    )
    def discover_test_files_tool(
        self,
        scope: Annotated[str, "Discovery scope"] = "all",
    ) -> Annotated[str, "JSON test discovery mapping"]:
        self._last_discovery = discover_test_files(self._files)
        return json.dumps(self._last_discovery, default=str)

    @kernel_function(
        name="analyze_test_coverage_tool",
        description="Analyze uploaded pytest-cov artifacts or static test-to-function mapping coverage.",
    )
    def analyze_test_coverage_tool(
        self,
        scope: Annotated[str, "Coverage scope"] = "all",
    ) -> Annotated[str, "JSON test coverage metrics and gaps"]:
        if not self._last_discovery:
            self._last_discovery = discover_test_files(self._files)
        result = analyze_test_coverage(self._files, self._last_discovery)
        return json.dumps(result, default=str)


def build_test_coverage_sk_agent(state: SharedChangeState, kernel: Kernel) -> StateAwareSKAgent:
    """Create Semantic Kernel Agent instance for ConcurrentOrchestration."""
    return StateAwareSKAgent(
        name="test_coverage_agent",
        description="Detects missing test files, untested functions, and missing test scenarios.",
        kernel=kernel,
        state=state,
        runner=run_test_coverage_agent,
    )


async def run_test_coverage_agent(
    state: SharedChangeState,
    kernel: Optional[Kernel] = None,
) -> dict[str, Any]:
    """Independently callable entrypoint for the Test-Coverage Agent."""
    agent_name = "test_coverage_agent"
    await state.mark_agent_running(agent_name, "Discovering test files and mapping production symbols...")

    try:
        active_kernel = kernel
        is_demo = state.data.submission_metadata.demo_mode
        if active_kernel is None:
            active_kernel, is_demo, _ = create_kernel(demo_mode=is_demo)

        plugin = TestCoverageAgentPlugin(files=state.data.files)
        plugin_name = f"test_tools_{uuid4().hex[:8]}"
        active_kernel.add_plugin(plugin, plugin_name=plugin_name)

        # Tool 1: discover_test_files via SK KernelFunction
        await state.update_agent_activity(agent_name, "Running discover_test_files", "discover_test_files")
        disc_res = await active_kernel.invoke(plugin_name=plugin_name, function_name="discover_test_files_tool")
        disc_data = json.loads(str(disc_res))

        # Tool 2: analyze_test_coverage via SK KernelFunction
        await state.update_agent_activity(agent_name, "Running analyze_test_coverage", "analyze_test_coverage")
        cov_res = await active_kernel.invoke(plugin_name=plugin_name, function_name="analyze_test_coverage_tool")
        cov_data = json.loads(str(cov_res))

        findings: list[Finding] = []
        prod_files = disc_data.get("production_files", [])
        untested = cov_data.get("untested_functions", [])

        if prod_files and not disc_data.get("has_tests"):
            findings.append(
                Finding(
                    id=f"test-missing-suite-{uuid4().hex[:6]}",
                    title="No test files submitted or mapped to modified code",
                    description=(
                        f"Production file(s) ({', '.join(prod_files[:4])}) have no corresponding test files "
                        "in this submission. Runtime coverage could not be verified without tests."
                    ),
                    severity=Severity.MEDIUM,
                    agent=agent_name,
                    category="testing",
                    file_path=prod_files[0],
                    line_start=1,
                    evidence=f"0 test files found for {len(prod_files)} production file(s).",
                    recommended_action="Add unit tests covering nominal behavior, edge cases, and error paths.",
                    rule_id="TEST-NO-FILES",
                    source="deterministic_tool",
                    confidence=0.93,
                )
            )
        elif untested:
            for sym in untested[:8]:
                findings.append(
                    Finding(
                        id=f"test-untested-fn-{uuid4().hex[:6]}",
                        title=f"Function '{sym['name']}' has no apparent test coverage",
                        description=(
                            f"Static test-mapping found no reference to `{sym['name']}` "
                            f"({sym['file_path']}:{sym['line_start']}) inside the submitted test files."
                        ),
                        severity=Severity.LOW,
                        agent=agent_name,
                        category="testing",
                        file_path=sym["file_path"],
                        line_start=sym["line_start"],
                        line_end=sym.get("line_end"),
                        evidence=f"Symbol '{sym['name']}' absent from {len(disc_data.get('test_files', []))} test file(s).",
                        recommended_action=f"Add targeted unit test(s) exercising `{sym['name']}` and its edge cases.",
                        rule_id="TEST-UNTESTED-SYMBOL",
                        source="deterministic_tool",
                        confidence=0.88,
                    )
                )

        await state.update_agent_activity(agent_name, "Generating test scenario recommendations...")
        sk_chat = ChatCompletionAgent(
            kernel=active_kernel,
            name="TestCoverageAgent",
            instructions=TEST_COVERAGE_INSTRUCTIONS,
        )
        evidence_ctx = {
            "test_files": disc_data.get("test_files", []),
            "production_files": prod_files,
            "untested_functions": untested[:15],
            "runtime_coverage_executed": cov_data.get("runtime_coverage_executed", False),
            "runtime_coverage_percent": cov_data.get("runtime_coverage_percent"),
            "static_symbol_coverage_percent": cov_data.get("static_symbol_coverage_percent"),
            "suggested_scenarios": cov_data.get("suggested_scenarios", []),
        }
        prompt = (
            "Evaluate test coverage and suggest missing test scenarios based strictly on this evidence.\n"
            f"TOOL_EVIDENCE_JSON:\n{json.dumps(evidence_ctx, indent=2)}"
        )

        summary = (
            f"Found {len(disc_data.get('test_files', []))} test file(s); "
            f"{len(untested)} untested symbol(s) detected via static mapping."
        )
        missing_scenarios = list(cov_data.get("suggested_scenarios", []))
        try:
            llm_data = await invoke_sk_agent_json(sk_chat, prompt)
            if llm_data.get("summary"):
                summary = str(llm_data["summary"])
            if llm_data.get("missing_scenarios"):
                missing_scenarios = [str(s) for s in llm_data["missing_scenarios"] if s]
        except LLMServiceError as llm_exc:
            summary += f" (LLM note unavailable: {llm_exc})"

        output_data = {
            "summary": summary,
            "existing_test_files": disc_data.get("test_files", []),
            "production_files": prod_files,
            "tested_symbols": disc_data.get("tested_symbols", []),
            "untested_functions": untested,
            "missing_scenarios": missing_scenarios,
            "runtime_coverage_executed": cov_data.get("runtime_coverage_executed", False),
            "runtime_coverage_percent": cov_data.get("runtime_coverage_percent"),
            "static_symbol_coverage_percent": cov_data.get("static_symbol_coverage_percent"),
            "coverage_note": cov_data.get("note"),
        }
        await state.mark_agent_completed(
            agent_name=agent_name,
            findings=findings,
            output_data=output_data,
            summary=summary,
            tools_invoked=["discover_test_files", "analyze_test_coverage"],
        )
        return output_data

    except Exception as exc:
        await state.mark_agent_failed(agent_name, str(exc))
        return {"error": str(exc)}

