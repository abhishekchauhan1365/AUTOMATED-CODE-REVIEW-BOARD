"""Semantic Kernel Fan-Out / Fan-In Multi-Agent Orchestration Workflow."""

from __future__ import annotations

from typing import Optional

from semantic_kernel.agents import ConcurrentOrchestration
from semantic_kernel.agents.runtime import InProcessRuntime

from agents.diff_agent import build_diff_sk_agent
from agents.fix_suggestion_agent import run_fix_suggestion_agent
from agents.reviewer_manager import run_reviewer_manager
from agents.security_agent import build_security_sk_agent
from agents.style_agent import build_style_sk_agent
from agents.test_coverage_agent import build_test_coverage_sk_agent
from orchestration.state import SharedChangeState
from services.llm_service import create_kernel
from tools.diff_parser import extract_modified_files


async def execute_review_workflow(
    state: SharedChangeState,
    demo_mode: Optional[bool] = None,
) -> SharedChangeState:
    """Execute the complete Fan-Out / Fan-In review workflow using Semantic Kernel."""
    requested_demo = demo_mode if demo_mode is not None else state.data.submission_metadata.demo_mode
    _, is_demo, model_id = create_kernel(demo_mode=requested_demo)
    state.data.submission_metadata.demo_mode = is_demo
    state.data.submission_metadata.model_used = model_id

    await state.mark_workflow_started()

    runtime: Optional[InProcessRuntime] = None
    try:
        # Pre-populate reconstructed SubmittedFile records when submission is a raw Git diff
        if state.data.git_diff and not state.data.files:
            extracted = extract_modified_files(git_diff=state.data.git_diff, submitted_files=[])
            state.data.files = extracted["submitted_files"]

        # Create isolated Kernel instances per parallel agent so plugin registrations are thread/async-safe
        k_diff, _, _ = create_kernel(demo_mode=is_demo)
        k_style, _, _ = create_kernel(demo_mode=is_demo)
        k_sec, _, _ = create_kernel(demo_mode=is_demo)
        k_test, _, _ = create_kernel(demo_mode=is_demo)
        k_mgr, _, _ = create_kernel(demo_mode=is_demo)
        k_fix, _, _ = create_kernel(demo_mode=is_demo)

        specialist_members = [
            build_diff_sk_agent(state, k_diff),
            build_style_sk_agent(state, k_style),
            build_security_sk_agent(state, k_sec),
            build_test_coverage_sk_agent(state, k_test),
        ]

        await state.mark_fan_out_started()

        runtime = InProcessRuntime()
        runtime.start()

        orchestration = ConcurrentOrchestration(members=specialist_members)
        task_prompt = (
            f"Execute specialist code review for Review ID {state.review_id}: "
            f"{state.data.submission_metadata.title}. "
            f"Files count: {len(state.data.files)}."
        )
        orchestration_result = await orchestration.invoke(task=task_prompt, runtime=runtime)
        await orchestration_result.get(timeout=120)

        await state.mark_fan_in_completed()

        # Agent 5: Reviewer Manager consolidation, deduplication, ranking, and decision
        await run_reviewer_manager(state, kernel=k_mgr)

        # Agent 6: Fix-Suggestion Agent proposes a patch for the single highest-severity finding
        await run_fix_suggestion_agent(state, kernel=k_fix)

        await state.mark_workflow_completed(failed=False)
    except Exception as exc:
        await state.mark_workflow_completed(failed=True, error=str(exc))
    finally:
        if runtime is not None:
            try:
                await runtime.stop_when_idle()
            except Exception:
                pass

    return state

