"""Agent 3: Security Agent — runs secret scanning and Bandit/AST static security analysis."""

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
from services.file_service import redact_secrets_in_text
from services.llm_service import LLMServiceError, create_kernel, invoke_sk_agent_json
from tools.secret_scanner import scan_for_secrets
from tools.security_scanner import run_security_analysis


SECURITY_AGENT_INSTRUCTIONS = """You are the Security Agent on an Automated Code Review Board.
Your deterministic scanners (secret_scanner and Bandit/AST security_scanner) have already inspected the code without executing it.
Interpret the evidence in TOOL_EVIDENCE_JSON and return strictly a JSON object with keys:
- "summary": concise 1-2 sentence security posture assessment.
- "contextual_notes": list of up to 3 mitigation priorities grounded strictly in the scanner findings.
- "additional_findings": list of additional vulnerability findings ONLY if clear evidence exists in the provided snippets (otherwise empty list).
Never expose raw secrets or fabricate vulnerabilities."""


class SecurityAgentPlugin:
    """Semantic Kernel plugin exposing Security Agent's two real Python tools."""

    def __init__(self, files: list[SubmittedFile]) -> None:
        self._files = files

    @kernel_function(
        name="scan_for_secrets_tool",
        description="Scan files for hardcoded API keys, passwords, tokens, and private keys.",
    )
    def scan_for_secrets_tool(
        self,
        scope: Annotated[str, "Scan scope"] = "all",
    ) -> Annotated[str, "JSON redacted secret scan findings"]:
        return json.dumps(scan_for_secrets(self._files), default=str)

    @kernel_function(
        name="run_security_analysis_tool",
        description="Run Bandit static analysis and AST/pattern vulnerability detection.",
    )
    def run_security_analysis_tool(
        self,
        scope: Annotated[str, "Analysis scope"] = "all",
    ) -> Annotated[str, "JSON static security analysis findings"]:
        return json.dumps(run_security_analysis(self._files), default=str)


def build_security_sk_agent(state: SharedChangeState, kernel: Kernel) -> StateAwareSKAgent:
    """Create Semantic Kernel Agent instance for ConcurrentOrchestration."""
    return StateAwareSKAgent(
        name="security_agent",
        description="Scans for hardcoded credentials, SQLi, unsafe shell/eval, and static vulnerabilities.",
        kernel=kernel,
        state=state,
        runner=run_security_agent,
    )


async def run_security_agent(
    state: SharedChangeState,
    kernel: Optional[Kernel] = None,
) -> dict[str, Any]:
    """Independently callable entrypoint for the Security Agent."""
    agent_name = "security_agent"
    await state.mark_agent_running(agent_name, "Scanning for hardcoded secrets and credentials...")

    try:
        active_kernel = kernel
        is_demo = state.data.submission_metadata.demo_mode
        if active_kernel is None:
            active_kernel, is_demo, _ = create_kernel(demo_mode=is_demo)

        plugin = SecurityAgentPlugin(files=state.data.files)
        plugin_name = f"security_tools_{uuid4().hex[:8]}"
        active_kernel.add_plugin(plugin, plugin_name=plugin_name)

        # Tool 1: scan_for_secrets via SK KernelFunction
        await state.update_agent_activity(agent_name, "Running secret & credential scanner", "scan_for_secrets")
        secret_res = await active_kernel.invoke(plugin_name=plugin_name, function_name="scan_for_secrets_tool")
        secret_data = json.loads(str(secret_res))

        # Tool 2: run_security_analysis via SK KernelFunction
        await state.update_agent_activity(agent_name, "Running Bandit & AST security analysis", "run_security_analysis")
        sec_res = await active_kernel.invoke(plugin_name=plugin_name, function_name="run_security_analysis_tool")
        sec_data = json.loads(str(sec_res))

        findings: list[Finding] = []
        for item in secret_data.get("secret_findings", []):
            sev_str = str(item.get("severity", "CRITICAL")).upper()
            sev = Severity[sev_str] if sev_str in Severity.__members__ else Severity.CRITICAL
            findings.append(
                Finding(
                    id=f"sec-cred-{uuid4().hex[:6]}",
                    title=str(item.get("title", "Hardcoded secret detected")),
                    description=redact_secrets_in_text(str(item.get("description", ""))),
                    severity=sev,
                    agent=agent_name,
                    category="security",
                    file_path=str(item.get("file_path", "unknown")),
                    line_start=item.get("line_start"),
                    line_end=item.get("line_end"),
                    evidence=redact_secrets_in_text(str(item.get("evidence", ""))),
                    recommended_action=str(item.get("recommended_action", "Move secret to environment variables.")),
                    rule_id=item.get("rule_id"),
                    source="deterministic_tool",
                    confidence=0.98,
                )
            )

        for item in sec_data.get("security_findings", []):
            sev_str = str(item.get("severity", "HIGH")).upper()
            sev = Severity[sev_str] if sev_str in Severity.__members__ else Severity.HIGH
            findings.append(
                Finding(
                    id=f"sec-vuln-{uuid4().hex[:6]}",
                    title=str(item.get("title", "Security vulnerability")),
                    description=redact_secrets_in_text(str(item.get("description", ""))),
                    severity=sev,
                    agent=agent_name,
                    category="security",
                    file_path=str(item.get("file_path", "unknown")),
                    line_start=item.get("line_start"),
                    line_end=item.get("line_end"),
                    evidence=redact_secrets_in_text(str(item.get("evidence", ""))),
                    recommended_action=str(item.get("recommended_action", "Apply secure coding remediation.")),
                    rule_id=item.get("rule_id"),
                    source="deterministic_tool",
                    confidence=0.94,
                )
            )

        await state.update_agent_activity(agent_name, "Explaining security findings with Semantic Kernel agent...")
        sk_chat = ChatCompletionAgent(
            kernel=active_kernel,
            name="SecurityAgent",
            instructions=SECURITY_AGENT_INSTRUCTIONS,
        )
        evidence_ctx = {
            "secret_findings": secret_data.get("secret_findings", [])[:15],
            "security_findings": sec_data.get("security_findings", [])[:20],
            "bandit_executed": sec_data.get("bandit_executed", False),
        }
        prompt = (
            "Summarize and prioritize these static security scanner findings.\n"
            f"TOOL_EVIDENCE_JSON:\n{json.dumps(evidence_ctx, indent=2)}"
        )

        summary = (
            f"Identified {len(secret_data.get('secret_findings', []))} secret issue(s) and "
            f"{len(sec_data.get('security_findings', []))} static vulnerability finding(s)."
        )
        contextual_notes: list[str] = []
        try:
            llm_data = await invoke_sk_agent_json(sk_chat, prompt)
            if llm_data.get("summary"):
                summary = redact_secrets_in_text(str(llm_data["summary"]))
            contextual_notes = [redact_secrets_in_text(str(n)) for n in llm_data.get("contextual_notes", []) if n]
        except LLMServiceError as llm_exc:
            summary += f" (LLM explanation unavailable: {llm_exc})"

        output_data = {
            "summary": summary,
            "contextual_notes": contextual_notes,
            "bandit_executed": sec_data.get("bandit_executed", False),
            "bandit_error": sec_data.get("bandit_error"),
            "secrets_count": len(secret_data.get("secret_findings", [])),
            "vulnerabilities_count": len(sec_data.get("security_findings", [])),
        }
        await state.mark_agent_completed(
            agent_name=agent_name,
            findings=findings,
            output_data=output_data,
            summary=summary,
            tools_invoked=["scan_for_secrets", "run_security_analysis"],
        )
        return output_data

    except Exception as exc:
        await state.mark_agent_failed(agent_name, redact_secrets_in_text(str(exc)))
        return {"error": redact_secrets_in_text(str(exc))}

