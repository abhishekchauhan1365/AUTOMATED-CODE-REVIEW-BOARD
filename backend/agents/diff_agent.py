"""Agent 1: Diff Agent — analyzes Git diffs, modified files, symbols, and risky changes."""

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
from tools.code_analyzer import analyze_code_structure
from tools.diff_parser import extract_modified_files, parse_git_diff


DIFF_AGENT_INSTRUCTIONS = """You are the Diff Agent on an Automated Code Review Board.
Your job is to interpret the parsed Git diff and code structure analysis provided in TOOL_EVIDENCE_JSON.
Return strictly a JSON object with keys:
- "change_summary": concise 2-3 sentence summary of what the code change accomplishes.
- "additional_findings": list of objects (only if evidence reveals a real architectural or regression risk; empty list otherwise), each with keys: title, description, severity (HIGH|MEDIUM|LOW|INFO), file_path, line_start, evidence, recommended_action.
Do NOT invent findings not grounded in the submitted diff or code structure."""


class DiffAgentPlugin:
    """Semantic Kernel plugin exposing Diff Agent's two real Python tools."""

    def __init__(self, files: list[SubmittedFile], git_diff: Optional[str]) -> None:
        self._files = files
        self._git_diff = git_diff

    @kernel_function(
        name="parse_git_diff_tool",
        description="Parse unified Git diff and extract modified/added/deleted files.",
    )
    def parse_git_diff_tool(
        self,
        include_raw: Annotated[bool, "Whether to parse diff text"] = True,
    ) -> Annotated[str, "JSON summary of parsed diff and modified files"]:
        if include_raw and self._git_diff:
            parsed = parse_git_diff(self._git_diff)
            extracted = extract_modified_files(git_diff=self._git_diff, submitted_files=self._files)
        else:
            extracted = extract_modified_files(git_diff=self._git_diff, submitted_files=self._files)
            parsed = extracted["diff_summary"]
        return json.dumps({"parsed": parsed, "file_records": extracted["file_records"]}, default=str)

    @kernel_function(
        name="analyze_code_structure_tool",
        description="Analyze functions, classes, imports, and risky structural patterns across files.",
    )
    def analyze_code_structure_tool(
        self,
        target: Annotated[str, "Target label"] = "all",
    ) -> Annotated[str, "JSON summary of code structure"]:
        result = analyze_code_structure(self._files)
        return json.dumps(result, default=str)


def build_diff_sk_agent(state: SharedChangeState, kernel: Kernel) -> StateAwareSKAgent:
    """Create a Semantic Kernel Agent instance for ConcurrentOrchestration."""
    return StateAwareSKAgent(
        name="diff_agent",
        description="Analyzes Git diffs, modified files, functions, and risky structural changes.",
        kernel=kernel,
        state=state,
        runner=run_diff_agent,
    )


async def run_diff_agent(
    state: SharedChangeState,
    kernel: Optional[Kernel] = None,
) -> dict[str, Any]:
    """Independently callable entrypoint for the Diff Agent."""
    agent_name = "diff_agent"
    await state.mark_agent_running(agent_name, "Parsing Git diff and extracting modified files...")

    try:
        active_kernel = kernel
        is_demo = state.data.submission_metadata.demo_mode
        if active_kernel is None:
            active_kernel, is_demo, _ = create_kernel(demo_mode=is_demo)

        plugin = DiffAgentPlugin(files=state.data.files, git_diff=state.data.git_diff)
        plugin_name = f"diff_tools_{uuid4().hex[:8]}"
        active_kernel.add_plugin(plugin, plugin_name=plugin_name)

        # Tool 1: parse_git_diff / extract_modified_files via SK KernelFunction
        await state.update_agent_activity(agent_name, "Running parse_git_diff & extract_modified_files", "parse_git_diff")
        diff_fn_res = await active_kernel.invoke(plugin_name=plugin_name, function_name="parse_git_diff_tool")
        diff_payload = json.loads(str(diff_fn_res))
        extracted = extract_modified_files(git_diff=state.data.git_diff, submitted_files=state.data.files)
        if not state.data.files and extracted["submitted_files"]:
            state.data.files = extracted["submitted_files"]
            plugin._files = state.data.files

        # Tool 2: analyze_code_structure via SK KernelFunction
        await state.update_agent_activity(agent_name, "Running analyze_code_structure", "analyze_code_structure")
        struct_fn_res = await active_kernel.invoke(plugin_name=plugin_name, function_name="analyze_code_structure_tool")
        structure_payload = json.loads(str(struct_fn_res))

        findings: list[Finding] = []
        for idx, risk in enumerate(structure_payload.get("risky_changes", []), start=1):
            findings.append(
                Finding(
                    id=f"diff-risk-{idx}-{uuid4().hex[:6]}",
                    title=f"Risky structural touch: {risk['reason']}",
                    description=(
                        f"Modified code at {risk['file_path']}:{risk['line']} touches "
                        f"{risk['reason'].lower()}, warranting careful security and behavioral review."
                    ),
                    severity=Severity.INFO,
                    agent=agent_name,
                    category="general",
                    file_path=risk["file_path"],
                    line_start=risk["line"],
                    line_end=risk["line"],
                    evidence=risk["snippet"],
                    recommended_action="Verify input validation, error handling, and test coverage around this change.",
                    rule_id="DIFF-RISKY-TOUCH",
                    source="deterministic_tool",
                    confidence=0.85,
                )
            )

        for f_info in structure_payload.get("files", []):
            if f_info.get("syntax_error"):
                findings.append(
                    Finding(
                        id=f"diff-syntax-{uuid4().hex[:6]}",
                        title=f"Python syntax error in {f_info['path']}",
                        description=f"AST parser reported a syntax error: {f_info['syntax_error']}",
                        severity=Severity.HIGH,
                        agent=agent_name,
                        category="correctness",
                        file_path=f_info["path"],
                        line_start=1,
                        evidence=f_info["syntax_error"],
                        recommended_action="Fix the syntax error before merging.",
                        rule_id="DIFF-SYNTAX-ERR",
                        source="deterministic_tool",
                        confidence=0.99,
                    )
                )

        # Invoke Semantic Kernel ChatCompletionAgent for contextual summary
        await state.update_agent_activity(agent_name, "Synthesizing change summary with Semantic Kernel agent...")
        sk_chat = ChatCompletionAgent(
            kernel=active_kernel,
            name="DiffAgent",
            instructions=DIFF_AGENT_INSTRUCTIONS,
        )
        evidence_ctx = {
            "description": state.data.submission_metadata.description,
            "modified_files": diff_payload.get("file_records", []),
            "important_functions": structure_payload.get("important_functions", [])[:25],
            "risky_changes": structure_payload.get("risky_changes", [])[:15],
            "total_additions": diff_payload.get("parsed", {}).get("total_additions", 0),
            "total_deletions": diff_payload.get("parsed", {}).get("total_deletions", 0),
        }
        prompt = (
            "Summarize this code change based strictly on the parsed diff and AST analysis.\n"
            f"TOOL_EVIDENCE_JSON:\n{json.dumps(evidence_ctx, indent=2)}"
        )

        change_summary = (
            f"Analyzed {len(evidence_ctx['modified_files'])} file(s) "
            f"(+{evidence_ctx['total_additions']}/-{evidence_ctx['total_deletions']} lines), "
            f"{len(evidence_ctx['important_functions'])} function(s), and "
            f"{len(evidence_ctx['risky_changes'])} risky touch(es)."
        )
        try:
            llm_data = await invoke_sk_agent_json(sk_chat, prompt)
            if llm_data.get("change_summary"):
                change_summary = str(llm_data["change_summary"])
            for extra in llm_data.get("additional_findings", []):
                if isinstance(extra, dict) and extra.get("title"):
                    sev_str = str(extra.get("severity", "INFO")).upper()
                    sev = Severity[sev_str] if sev_str in Severity.__members__ else Severity.INFO
                    findings.append(
                        Finding(
                            id=f"diff-llm-{uuid4().hex[:6]}",
                            title=str(extra["title"])[:140],
                            description=str(extra.get("description", "")),
                            severity=sev,
                            agent=agent_name,
                            category="general",
                            file_path=str(extra.get("file_path", "unknown")),
                            line_start=extra.get("line_start"),
                            evidence=str(extra.get("evidence", ""))[:180],
                            recommended_action=str(extra.get("recommended_action", "Review change carefully.")),
                            source="demo_mode" if is_demo else "llm_analysis",
                            confidence=0.75,
                        )
                    )
        except LLMServiceError as llm_exc:
            change_summary += f" (LLM summary unavailable: {llm_exc})"

        output_data = {
            "change_summary": change_summary,
            "modified_files": diff_payload.get("file_records", []),
            "total_additions": evidence_ctx["total_additions"],
            "total_deletions": evidence_ctx["total_deletions"],
            "important_functions": structure_payload.get("important_functions", []),
            "risky_changes": structure_payload.get("risky_changes", []),
            "file_structures": structure_payload.get("files", []),
        }
        await state.mark_agent_completed(
            agent_name=agent_name,
            findings=findings,
            output_data=output_data,
            summary=change_summary,
            tools_invoked=["parse_git_diff", "analyze_code_structure"],
        )
        return output_data

    except Exception as exc:
        await state.mark_agent_failed(agent_name, str(exc))
        return {"error": str(exc)}

