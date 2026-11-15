"""Review lifecycle service managing active runs, persistence, and live streams."""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from database.db import (
    approve_review_patch,
    delete_review,
    get_dashboard_stats,
    get_review_detail,
    init_db,
    list_reviews,
    save_review_state,
)
from orchestration.schemas import (
    FixSuggestion,
    ReviewDetailResponse,
    ReviewStatusResponse,
    ReviewSummaryItem,
    SubmissionMetadata,
    SubmittedFile,
    utc_now_iso,
)
from orchestration.state import SharedChangeState
from orchestration.workflow import execute_review_workflow
from services.file_service import (
    FileValidationError,
    MAX_DIFF_SIZE_BYTES,
    validate_and_build_submitted_files,
)
from services.llm_service import is_demo_mode_enabled
from services.report_service import append_execution_event, read_review_logs

_ACTIVE_STATES: dict[str, SharedChangeState] = {}
_BACKGROUND_TASKS: dict[str, asyncio.Task[Any]] = {}


def initialize_storage() -> None:
    """Initialize SQLite tables on startup."""
    init_db()


def get_active_state(review_id: str) -> Optional[SharedChangeState]:
    """Return active in-memory SharedChangeState if review is currently running or cached."""
    return _ACTIVE_STATES.get(review_id)


async def start_review(
    title: Optional[str],
    description: str,
    submission_type: str,
    git_diff: Optional[str] = None,
    raw_files: Optional[list[dict[str, Any]]] = None,
    demo_mode: Optional[bool] = None,
    run_async: bool = True,
) -> ReviewDetailResponse:
    """Validate submission, initialize SharedChangeState, and launch the multi-agent workflow."""
    validated_files: list[SubmittedFile] = []
    clean_diff: Optional[str] = None

    if submission_type == "diff":
        if not git_diff or not git_diff.strip():
            raise FileValidationError("Git diff text cannot be empty when submission_type is 'diff'.")
        if len(git_diff.encode("utf-8")) > MAX_DIFF_SIZE_BYTES:
            raise FileValidationError("Submitted Git diff exceeds maximum allowed size (2 MB).")
        clean_diff = git_diff
    else:
        validated_files = validate_and_build_submitted_files(raw_files or [])

    use_demo = is_demo_mode_enabled(demo_mode)
    auto_title = title.strip() if title and title.strip() else (
        f"Git Diff Review ({len((clean_diff or '').splitlines())} lines)"
        if submission_type == "diff"
        else f"File Review ({len(validated_files)} file{'s' if len(validated_files) != 1 else ''})"
    )

    metadata = SubmissionMetadata(
        title=auto_title,
        description=description.strip(),
        submission_type="diff" if submission_type == "diff" else "files",
        demo_mode=use_demo,
    )

    state = SharedChangeState(
        submission_metadata=metadata,
        files=validated_files,
        git_diff=clean_diff,
        event_sink=append_execution_event,
    )
    _ACTIVE_STATES[state.review_id] = state
    save_review_state(state.to_detail_response())

    async def _runner() -> None:
        try:
            await execute_review_workflow(state, demo_mode=use_demo)
        finally:
            save_review_state(state.to_detail_response())

    if run_async:
        task = asyncio.create_task(_runner())
        _BACKGROUND_TASKS[state.review_id] = task
        task.add_done_callback(lambda _t: _BACKGROUND_TASKS.pop(state.review_id, None))
    else:
        await _runner()

    return state.to_detail_response()


def get_status(review_id: str) -> Optional[ReviewStatusResponse]:
    """Return live execution status from active state or SQLite."""
    active = _ACTIVE_STATES.get(review_id)
    if active is not None:
        return active.to_status_response()
    detail = get_review_detail(review_id)
    if detail is None:
        return None
    return ReviewStatusResponse(
        review_id=detail.review_id,
        overall_status=detail.overall_status,
        phase="completed" if detail.overall_status == "completed" else detail.overall_status,
        demo_mode=detail.submission_metadata.demo_mode,
        agent_statuses=detail.agent_statuses,
        timestamps=detail.execution_timestamps,
    )


def get_detail(review_id: str) -> Optional[ReviewDetailResponse]:
    """Return complete review details from active state or SQLite."""
    active = _ACTIVE_STATES.get(review_id)
    if active is not None:
        return active.to_detail_response()
    return get_review_detail(review_id)


def get_patch(review_id: str) -> Optional[FixSuggestion]:
    """Return Fix-Suggestion Agent output for a review."""
    detail = get_detail(review_id)
    if detail is None:
        return None
    return detail.fix_suggestion


def approve_patch(review_id: str) -> Optional[FixSuggestion]:
    """Record explicit user approval on the proposed patch."""
    active = _ACTIVE_STATES.get(review_id)
    if active is not None and active.data.fix_suggestion and active.data.fix_suggestion.available:
        active.data.fix_suggestion.user_approved = True
        active.data.fix_suggestion.approved_at = utc_now_iso()
        save_review_state(active.to_detail_response())
        return active.data.fix_suggestion

    updated = approve_review_patch(review_id)
    if updated is None:
        return None
    return updated.fix_suggestion


def get_logs(review_id: str) -> list[dict[str, Any]]:
    """Return review execution trace from JSONL log or fallback to state events."""
    logged = read_review_logs(review_id=review_id)
    if logged:
        return logged
    detail = get_detail(review_id)
    if detail is None:
        return []
    return [ev.model_dump() for ev in detail.events]


def remove_review(review_id: str) -> bool:
    """Remove review from active cache and SQLite."""
    _ACTIVE_STATES.pop(review_id, None)
    return delete_review(review_id)


def list_history() -> list[ReviewSummaryItem]:
    """Return persisted review history merged with any running reviews."""
    return list_reviews()


def fetch_stats() -> dict[str, Any]:
    """Return real aggregated dashboard metrics."""
    return get_dashboard_stats()

