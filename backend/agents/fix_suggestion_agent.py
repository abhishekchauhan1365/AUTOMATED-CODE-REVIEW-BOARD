"""Agent 6: Fix-Suggestion Agent — proposes a validated unified diff patch for top finding."""

from __future__ import annotations

import json
import re
from typing import Annotated, Any, Optional
from uuid import uuid4

from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.functions import kernel_function

from orchestration.schemas import Finding, FixSuggestion, SEVERITY_ORDER, Severity, SubmittedFile
from orchestration.state import SharedChangeState
from services.file_service import redact_secrets_in_text
from services.llm_service import LLMServiceError, create_kernel, invoke_sk_agent_json
from tools.context_extractor import extract_code_context
from tools.patch_generator import generate_unified_patch, validate_patch


FIX_SUGGESTION_INSTRUCTIONS = """You are the Fix-Suggestion Agent on an Automated Code Review Board.
You receive the single highest-severity actionable finding and its exact surrounding source code context in TOOL_EVIDENCE_JSON.
Return strictly a JSON object with keys:
- "suggested_replacement": the exact replacement code lines for lines [line_start..line_end] ONLY (preserving indentation, no markdown fences, valid syntax).
- "explanation": clear 2-3 sentence explanation of why this replacement resolves the finding safely.
Safety rules:
- Never introduce hardcoded secrets or unsafe shell/eval calls.
- Preserve surrounding behavior and indentation."""


class FixSuggestionPlugin:
    """Semantic Kernel plugin exposing Fix-Suggestion Agent's two real Python tools."""

    def __init__(self, files: list[SubmittedFile]) -> None:
        self._files = files

    @kernel_function(
        name="extract_code_context_tool",
        description="Extract target lines and surrounding source context for a finding.",
    )
    def extract_code_context_tool(
        self,
        file_path: Annotated[str, "Target file path"],
        line_start: Annotated[int, "1-based start line"],
        line_end: Annotated[int, "1-based end line"],
    ) -> Annotated[str, "JSON source context"]:
        ctx = extract_code_context(self._files, file_path, line_start, line_end)
        return json.dumps(ctx, default=str)

    @kernel_function(
        name="generate_and_validate_patch_tool",
        description="Generate a unified diff patch and statically validate its syntax and diff structure.",
    )
    def generate_and_validate_patch_tool(
        self,
        file_path: Annotated[str, "Target file path"],
        original_content: Annotated[str, "Full original file text"],
        replacement_block: Annotated[str, "Proposed replacement lines"],
        line_start: Annotated[int, "1-based start line"],
        line_end: Annotated[int, "1-based end line"],
        language: Annotated[str, "Programming language"] = "python",
    ) -> Annotated[str, "JSON unified patch and validation status"]:
        gen = generate_unified_patch(
            file_path=file_path,
            original_content=original_content,
            replacement_block=replacement_block,
            line_start=line_start,
            line_end=line_end,
        )
        val = validate_patch(
            file_path=file_path,
            patched_content=gen.get("patched_content", ""),
            patch_text=gen.get("patch", ""),
            language=language,
        )
        return json.dumps({"generation": gen, "validation": val}, default=str)


def _select_highest_priority_finding(
    findings: list[Finding],
    files: list[SubmittedFile],
) -> Optional[Finding]:
    """Select the single highest-severity actionable finding that maps to an editable file."""
    file_map = {sf.path.replace("\\", "/").lstrip("./").lower(): sf for sf in files if sf.status != "deleted"}
    ordered = sorted(
        findings,
        key=lambda f: (
            -SEVERITY_ORDER[f.severity],
            0 if f.category.lower() == "security" else 1,
            -(1 if f.line_start else 0),
        ),
    )
    for f in ordered:
        norm = f.file_path.replace("\\", "/").lstrip("./").lower()
        sf = file_map.get(norm)
        if sf and sf.content.strip() and f.severity != Severity.INFO:
            return f
    return None


def _build_deterministic_fix(finding: Finding, ctx: dict[str, Any]) -> tuple[str, str]:
    """Generate a safe deterministic replacement and explanation for well-known vulnerability/style patterns."""
    target = ctx.get("target_code", "")
    indent = ctx.get("leading_indent", "")
    rule = (finding.rule_id or "").upper()
    title_l = finding.title.lower()

    # 1. Hardcoded secret/password/API key assignment
    if rule.startswith("SEC-KEY-") or rule == "SEC-CRED-ASSIGN" or "hardcoded" in title_l or "secret" in title_l:
        assign_match = re.match(r"^(\s*)([A-Za-z_]\w*)\s*=\s*['\"].*['\"](\s*(?:#.*)?)$", target)
        if assign_match:
            ind, var_name, trailing = assign_match.groups()
            env_name = re.sub(r"[^A-Z0-9_]", "_", var_name.upper())
            if ctx.get("language") == "python":
                replacement = f'{ind}{var_name} = os.getenv("{env_name}", ""){trailing}'
                return (
                    replacement,
                    f"Reads `{var_name}` from environment variable `{env_name}` instead of hardcoding a credential in source code.",
                )
            elif ctx.get("language") in ("javascript", "typescript"):
                replacement = f"{ind}const {var_name} = process.env.{env_name} ?? '';"
                return (
                    replacement,
                    f"Loads `{var_name}` from `process.env.{env_name}` instead of embedding a hardcoded secret.",
                )

    # 2. eval() -> ast.literal_eval()
    if "eval" in title_l or rule in ("SEC-EVAL-EXEC", "B307"):
        if "eval(" in target and ctx.get("language") == "python":
            replacement = target.replace("eval(", "ast.literal_eval(")
            return (
                replacement,
                "Replaces `eval(...)` with `ast.literal_eval(...)` (ensure `import ast` is present) to prevent arbitrary code execution.",
            )

    # 3. subprocess shell=True -> shell=False
    if "shell=true" in target.lower() or "shell" in title_l or rule in ("SEC-SHELL-TRUE", "B602"):
        if "shell=True" in target:
            replacement = target.replace("shell=True", "shell=False")
            return (
                replacement,
                "Disables `shell=True` so arguments are not interpreted by a system shell, mitigating OS command injection.",
            )

    # 4. SQL injection via f-string in .execute(f"SELECT ... {var}")
    if "sql" in title_l or rule in ("SEC-SQLI-FMT", "SEC-AST-SQLI", "B608"):
        sqli_match = re.search(r"""(\.execute(?:many)?\s*\()\s*f(['"])(.*?)\2\s*(\))""", target)
        if sqli_match:
            prefix, quote, query_body, suffix = sqli_match.groups()
            vars_found = re.findall(r"\{([A-Za-z_][A-Za-z0-9_.]*)\}", query_body)
            if vars_found:
                param_query = re.sub(r"['\"]?\{[A-Za-z_][A-Za-z0-9_.]*\}['\"]?", "?", query_body)
                tuple_args = ", ".join(vars_found) + ("," if len(vars_found) == 1 else "")
                before = target[: sqli_match.start()]
                after = target[sqli_match.end() :]
                replacement = f'{before}{prefix}{quote}{param_query}{quote}, ({tuple_args}){suffix}{after}'
                return (
                    replacement,
                    "Converts interpolated f-string SQL query into a parameterized query with `?` placeholders and bound parameters.",
                )

    # 5. TLS verify=False -> verify=True
    if "verify=false" in target.lower() or rule == "SEC-TLS-VERIFY":
        replacement = re.sub(r"verify\s*=\s*False", "verify=True", target)
        return (
            replacement,
            "Restores TLS certificate validation (`verify=True`) to prevent man-in-the-middle attacks.",
        )

    # 6. Weak hash md5/sha1 -> sha256
    if "md5" in target.lower() or "sha1" in target.lower() or rule in ("SEC-WEAK-HASH", "B324"):
        replacement = re.sub(r"hashlib\.(?:md5|sha1)\(", "hashlib.sha256(", target)
        return (
            replacement,
            "Upgrades weak MD5/SHA-1 digest to SHA-256 (`hashlib.sha256`).",
        )

    # 7. yaml.load -> yaml.safe_load
    if "yaml.load(" in target:
        replacement = re.sub(r"yaml\.load\(([^,)]+)(?:,\s*Loader=[^)]+)?\)", r"yaml.safe_load(\1)", target)
        return (
            replacement,
            "Replaces unsafe `yaml.load(...)` with `yaml.safe_load(...)` to prevent arbitrary object instantiation.",
        )

    # 8. JS innerHTML -> textContent
    if ".innerHTML" in target:
        replacement = target.replace(".innerHTML", ".textContent")
        return (
            replacement,
            "Replaces `.innerHTML` assignment with `.textContent` so untrusted strings are safely text-encoded.",
        )

    # 9. Generic fallback: add TODO remediation comment without breaking syntax
    comment_prefix = "#" if ctx.get("language") == "python" else "//"
    replacement = f"{indent}{comment_prefix} REVIEW FIX ({finding.severity.value}): {finding.recommended_action}\n{target}"
    return (
        replacement,
        f"Annotated `{finding.file_path}:{finding.line_start}` with remediation guidance because an automated rewrite requires broader context.",
    )


async def run_fix_suggestion_agent(
    state: SharedChangeState,
    kernel: Optional[Kernel] = None,
) -> dict[str, Any]:
    """Independently callable entrypoint for the Fix-Suggestion Agent."""
    agent_name = "fix_suggestion_agent"
    await state.mark_agent_running(agent_name, "Selecting highest-severity actionable finding...")

    try:
        active_kernel = kernel
        is_demo = state.data.submission_metadata.demo_mode
        if active_kernel is None:
            active_kernel, is_demo, _ = create_kernel(demo_mode=is_demo)

        selected = _select_highest_priority_finding(state.data.consolidated_findings, state.data.files)
        if selected is None:
            no_fix = FixSuggestion(
                available=False,
                explanation="No actionable code-level findings (LOW or above) require a patch.",
                validation_status="unavailable",
                validation_message="No patch needed.",
            )
            await state.set_fix_suggestion(no_fix)
            await state.mark_agent_completed(
                agent_name=agent_name,
                findings=[],
                output_data={"available": False, "reason": no_fix.explanation},
                summary="No actionable code finding required a patch.",
                tools_invoked=[],
            )
            return {"available": False}

        plugin = FixSuggestionPlugin(files=state.data.files)
        plugin_name = f"fix_tools_{uuid4().hex[:8]}"
        active_kernel.add_plugin(plugin, plugin_name=plugin_name)

        # Tool 1: extract_code_context via SK KernelFunction
        await state.update_agent_activity(
            agent_name,
            f"Extracting context for {selected.file_path}:{selected.line_start or 1}",
            "extract_code_context",
        )
        ctx_raw = await active_kernel.invoke(
            plugin_name=plugin_name,
            function_name="extract_code_context_tool",
            file_path=selected.file_path,
            line_start=selected.line_start or 1,
            line_end=selected.line_end or selected.line_start or 1,
        )
        ctx_data = json.loads(str(ctx_raw))

        if not ctx_data.get("found"):
            unavailable_fix = FixSuggestion(
                available=False,
                selected_finding=selected,
                file_path=selected.file_path,
                explanation=f"Unable to generate safe patch: {ctx_data.get('error', 'source context unavailable')}.",
                validation_status="unavailable",
                validation_message=ctx_data.get("error", "Context unavailable"),
            )
            await state.set_fix_suggestion(unavailable_fix)
            await state.mark_agent_completed(
                agent_name=agent_name,
                findings=[],
                output_data={"available": False, "reason": unavailable_fix.explanation},
                summary=unavailable_fix.explanation,
                tools_invoked=["extract_code_context"],
            )
            return {"available": False}

        det_replacement, det_explanation = _build_deterministic_fix(selected, ctx_data)

        # Invoke Semantic Kernel ChatCompletionAgent for patch refinement
        await state.update_agent_activity(agent_name, "Proposing safe replacement with Semantic Kernel agent...")
        sk_chat = ChatCompletionAgent(
            kernel=active_kernel,
            name="FixSuggestionAgent",
            instructions=FIX_SUGGESTION_INSTRUCTIONS,
        )
        evidence_ctx = {
            "selected_finding": {
                "title": selected.title,
                "description": redact_secrets_in_text(selected.description),
                "severity": selected.severity.value,
                "file_path": selected.file_path,
                "line_start": ctx_data["line_start"],
                "line_end": ctx_data["line_end"],
                "recommended_action": selected.recommended_action,
            },
            "numbered_context": redact_secrets_in_text(ctx_data["numbered_context"]),
            "target_code": redact_secrets_in_text(ctx_data["target_code"]),
            "deterministic_replacement": det_replacement,
            "deterministic_explanation": det_explanation,
        }
        prompt = (
            "Propose a clean, minimal replacement for `target_code` that resolves the selected finding.\n"
            f"TOOL_EVIDENCE_JSON:\n{json.dumps(evidence_ctx, indent=2)}"
        )

        replacement_code = det_replacement
        explanation = det_explanation
        try:
            llm_data = await invoke_sk_agent_json(sk_chat, prompt)
            candidate_rep = str(llm_data.get("suggested_replacement") or "").strip("\n")
            if candidate_rep and candidate_rep != ctx_data["target_code"]:
                replacement_code = candidate_rep
            if llm_data.get("explanation"):
                explanation = redact_secrets_in_text(str(llm_data["explanation"]))
        except LLMServiceError:
            pass

        # Tool 2: generate_unified_patch + validate_patch via SK KernelFunction
        await state.update_agent_activity(agent_name, "Generating and validating unified diff patch", "generate_unified_patch")
        patch_raw = await active_kernel.invoke(
            plugin_name=plugin_name,
            function_name="generate_and_validate_patch_tool",
            file_path=ctx_data["file_path"],
            original_content=ctx_data["full_content"],
            replacement_block=replacement_code,
            line_start=ctx_data["line_start"],
            line_end=ctx_data["line_end"],
            language=ctx_data.get("language", "python"),
        )
        patch_res = json.loads(str(patch_raw))
        gen = patch_res["generation"]
        val = patch_res["validation"]

        # If LLM's replacement failed static AST validation, fall back to deterministic validated patch
        if not val.get("valid") and replacement_code != det_replacement:
            replacement_code = det_replacement
            explanation = det_explanation
            patch_raw = await active_kernel.invoke(
                plugin_name=plugin_name,
                function_name="generate_and_validate_patch_tool",
                file_path=ctx_data["file_path"],
                original_content=ctx_data["full_content"],
                replacement_block=replacement_code,
                line_start=ctx_data["line_start"],
                line_end=ctx_data["line_end"],
                language=ctx_data.get("language", "python"),
            )
            patch_res = json.loads(str(patch_raw))
            gen = patch_res["generation"]
            val = patch_res["validation"]

        fix_obj = FixSuggestion(
            available=bool(gen.get("success")),
            selected_finding=selected,
            file_path=ctx_data["file_path"],
            line_start=ctx_data["line_start"],
            line_end=ctx_data["line_end"],
            original_code=redact_secrets_in_text(ctx_data["target_code"]),
            suggested_replacement=replacement_code,
            explanation=explanation,
            proposed_patch=redact_secrets_in_text(gen.get("patch", "")),
            validation_status=val.get("status", "invalid"),
            validation_message=val.get("message", ""),
            requires_explicit_approval=True,
            user_approved=False,
        )
        await state.set_fix_suggestion(fix_obj)

        summary = (
            f"Proposed validated unified diff patch for {selected.severity.value} finding "
            f"'{selected.title}' in {fix_obj.file_path}:{fix_obj.line_start}."
        )
        output_data = {
            "available": fix_obj.available,
            "file_path": fix_obj.file_path,
            "line_start": fix_obj.line_start,
            "validation_status": fix_obj.validation_status,
            "selected_finding_title": selected.title,
        }
        await state.mark_agent_completed(
            agent_name=agent_name,
            findings=[],
            output_data=output_data,
            summary=summary,
            tools_invoked=["extract_code_context", "generate_unified_patch", "validate_patch"],
        )
        return output_data

    except Exception as exc:
        await state.mark_agent_failed(agent_name, redact_secrets_in_text(str(exc)))
        return {"error": redact_secrets_in_text(str(exc))}

