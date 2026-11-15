"""Reusable Semantic Kernel + Groq LLM service with Mock/Demo fallback and resilient retries."""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any, AsyncGenerator, Optional

from dotenv import load_dotenv
from openai import APITimeoutError, AsyncOpenAI, RateLimitError
from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.streaming_chat_message_content import StreamingChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole

from services.file_service import redact_secrets_in_text

load_dotenv()

DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


class LLMServiceError(RuntimeError):
    """Raised when the LLM provider fails after retries."""


def is_demo_mode_enabled(requested_demo_mode: Optional[bool] = None) -> bool:
    """Determine whether demo/mock LLM mode should be used."""
    if requested_demo_mode is True:
        return True
    env_mock = os.getenv("USE_MOCK_LLM", "false").strip().lower() in ("1", "true", "yes")
    if env_mock:
        return True
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key == "your_groq_api_key_here" or api_key.startswith("your_"):
        return True
    if requested_demo_mode is False:
        return False
    return False


class MockGroqChatCompletion(ChatCompletionClientBase):
    """Semantic Kernel ChatCompletionClientBase implementation for deterministic Demo Mode.

    This allows the complete Semantic Kernel ChatCompletionAgent + ConcurrentOrchestration
    pipeline to execute end-to-end without a paid Groq API key, clearly distinguishing
    demo contextual summaries from deterministic static-analysis tool evidence.
    """

    ai_model_id: str = "demo-deterministic-groq-simulator"

    async def _inner_get_chat_message_contents(
        self,
        chat_history: ChatHistory,
        settings: PromptExecutionSettings,
    ) -> list[ChatMessageContent]:
        system_text = ""
        user_text = ""
        for msg in chat_history.messages:
            if msg.role == AuthorRole.SYSTEM:
                system_text += str(msg.content) + "\n"
            elif msg.role == AuthorRole.USER:
                user_text += str(msg.content) + "\n"

        response_payload = _build_demo_agent_json(system_text, user_text)
        return [
            ChatMessageContent(
                role=AuthorRole.ASSISTANT,
                content=json.dumps(response_payload),
            )
        ]

    async def _inner_get_streaming_chat_message_contents(
        self,
        chat_history: ChatHistory,
        settings: PromptExecutionSettings,
    ) -> AsyncGenerator[list[StreamingChatMessageContent], Any]:
        contents = await self._inner_get_chat_message_contents(chat_history, settings)
        yield [
            StreamingChatMessageContent(
                role=AuthorRole.ASSISTANT,
                choice_index=0,
                content=contents[0].content,
            )
        ]


def _extract_embedded_context(user_text: str) -> dict[str, Any]:
    """Extract the JSON evidence payload embedded in agent prompts if present."""
    marker = "TOOL_EVIDENCE_JSON:"
    if marker in user_text:
        after = user_text.split(marker, 1)[1].strip()
        try:
            # Find outermost JSON object
            start = after.find("{")
            if start != -1:
                decoder = json.JSONDecoder()
                obj, _ = decoder.raw_decode(after[start:])
                if isinstance(obj, dict):
                    return obj
        except Exception:
            pass
    return {}


def _build_demo_agent_json(system_text: str, user_text: str) -> dict[str, Any]:
    """Generate structured demo interpretation grounded strictly in real tool evidence."""
    ctx = _extract_embedded_context(user_text)
    lower_sys = system_text.lower()

    if "diff agent" in lower_sys:
        files = ctx.get("modified_files", [])
        risks = ctx.get("risky_changes", [])
        funcs = ctx.get("important_functions", [])
        return {
            "change_summary": (
                f"[Demo AI Analysis] Reviewed {len(files)} file(s) with "
                f"{len(funcs)} extracted symbol(s) and {len(risks)} potentially risky structural touch(es)."
            ),
            "additional_findings": [],
            "demo_mode": True,
        }

    if "style agent" in lower_sys:
        lint_count = len(ctx.get("lint_issues", []))
        complex_count = len(ctx.get("complexity_issues", []))
        dup_count = len(ctx.get("duplication_issues", []))
        return {
            "summary": (
                f"[Demo AI Analysis] Interpreted {lint_count} lint issue(s), "
                f"{complex_count} complexity warning(s), and {dup_count} duplication block(s)."
            ),
            "contextual_notes": [
                "Prioritize decomposing high-complexity functions and resolving linter errors before merge."
                if (lint_count + complex_count + dup_count) > 0
                else "Code formatting, naming conventions, and complexity metrics look clean."
            ],
            "additional_findings": [],
            "demo_mode": True,
        }

    if "security agent" in lower_sys:
        sec_count = len(ctx.get("security_findings", []))
        secret_count = len(ctx.get("secret_findings", []))
        return {
            "summary": (
                f"[Demo AI Analysis] Evaluated {secret_count} secret detection(s) and "
                f"{sec_count} static security pattern finding(s)."
            ),
            "contextual_notes": [
                "Critical/high static security evidence requires immediate remediation before approval."
                if (sec_count + secret_count) > 0
                else "No hardcoded secrets or unsafe static execution patterns detected by scanners."
            ],
            "additional_findings": [],
            "demo_mode": True,
        }

    if "test-coverage agent" in lower_sys:
        test_files = ctx.get("test_files", [])
        untested = ctx.get("untested_functions", [])
        scenarios = ctx.get("suggested_scenarios", [])
        return {
            "summary": (
                f"[Demo AI Analysis] Found {len(test_files)} test file(s); identified "
                f"{len(untested)} potentially untested function(s) via static symbol mapping."
            ),
            "missing_scenarios": scenarios[:5],
            "additional_findings": [],
            "demo_mode": True,
        }

    if "reviewer manager" in lower_sys:
        decision = ctx.get("recommended_decision", "APPROVE")
        blocking = ctx.get("blocking_count", 0)
        total = ctx.get("total_consolidated", 0)
        return {
            "decision": decision,
            "reasoning": (
                f"[Demo AI Analysis] Based on {total} consolidated finding(s) ({blocking} blocking), "
                f"the Reviewer Manager recommends {decision}."
            ),
            "demo_mode": True,
        }

    if "fix-suggestion agent" in lower_sys:
        finding = ctx.get("selected_finding") or {}
        proposed = ctx.get("deterministic_replacement")
        explanation = ctx.get("deterministic_explanation") or (
            f"[Demo AI Analysis] Replaces the vulnerable/problematic construct in "
            f"{finding.get('file_path', 'target file')} with a safer implementation."
        )
        return {
            "suggested_replacement": proposed or "",
            "explanation": explanation,
            "demo_mode": True,
        }

    return {"summary": "[Demo AI Analysis] Completed evaluation.", "demo_mode": True}


def create_kernel(demo_mode: Optional[bool] = None, service_id: str = "groq_llm") -> tuple[Kernel, bool, str]:
    """Create a Semantic Kernel instance configured for Groq or Demo Mode.

    Returns:
        Tuple of (kernel, is_demo, model_name).
    """
    kernel = Kernel()
    use_demo = is_demo_mode_enabled(demo_mode)

    if use_demo:
        mock_service = MockGroqChatCompletion(service_id=service_id)
        kernel.add_service(mock_service)
        return kernel, True, mock_service.ai_model_id

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    base_url = os.getenv("GROQ_BASE_URL", DEFAULT_GROQ_BASE_URL).strip()
    model_id = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip()
    timeout_s = float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout_s,
    )
    chat_service = OpenAIChatCompletion(
        service_id=service_id,
        ai_model_id=model_id,
        async_client=client,
    )
    kernel.add_service(chat_service)
    return kernel, False, model_id


def extract_json_from_text(raw_text: str) -> dict[str, Any]:
    """Safely parse JSON from an LLM response, stripping markdown code fences if present."""
    if not raw_text:
        raise ValueError("Empty LLM response.")

    cleaned = raw_text.strip()
    # Strip ```json ... ``` blocks
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, flags=re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Fallback: locate first '{' and decode object
    start = cleaned.find("{")
    if start != -1:
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(cleaned[start:])
        if isinstance(obj, dict):
            return obj

    raise ValueError("Model response did not contain a valid JSON object.")


async def invoke_sk_agent_json(
    agent: ChatCompletionAgent,
    prompt: str,
    max_retries: int = 2,
    timeout_seconds: Optional[float] = None,
) -> dict[str, Any]:
    """Invoke a Semantic Kernel ChatCompletionAgent with retries, timeout, and safe JSON parsing."""
    timeout = timeout_seconds or float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            response = await asyncio.wait_for(agent.get_response(messages=prompt), timeout=timeout)
            text = str(response.message.content) if response and response.message else ""
            return extract_json_from_text(text)
        except (APITimeoutError, asyncio.TimeoutError) as exc:
            last_error = LLMServiceError(f"LLM request timed out after {timeout}s.")
            if attempt < max_retries:
                await asyncio.sleep(0.75 * (attempt + 1))
        except RateLimitError as exc:
            last_error = LLMServiceError("Groq API rate limit exceeded. Try again shortly or enable Demo Mode.")
            if attempt < max_retries:
                await asyncio.sleep(1.5 * (attempt + 1))
        except ValueError as exc:
            last_error = LLMServiceError(f"Invalid structured JSON from LLM: {exc}")
            if attempt < max_retries:
                await asyncio.sleep(0.3)
        except Exception as exc:
            safe_msg = redact_secrets_in_text(str(exc))
            last_error = LLMServiceError(f"LLM invocation error: {safe_msg}")
            if attempt < max_retries:
                await asyncio.sleep(0.5)

    raise last_error or LLMServiceError("Unknown LLM invocation failure.")

