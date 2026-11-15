"""Shared Change-State object read and mutated by all agents in the workflow."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from orchestration.schemas import (
    AgentExecutionState,
    AgentStatusRecord,
    ExecutionEvent,
    ExecutionTimestamps,
    Finding,
    FixSuggestion,
    MergeRecommendation,
    ReviewDetailResponse,
    ReviewStatusResponse,
    Severity,
    SubmissionMetadata,
    SubmittedFile,
    utc_now_iso,
)


AGENT_DEFINITIONS: list[tuple[str, str, str]] = [
    ("diff_agent", "Diff Agent", "Parses diffs, files, functions, and risky structural changes"),
    ("style_agent", "Style Agent", "Runs deterministic linters, complexity, and duplication analysis"),
    ("security_agent", "Security Agent", "Scans for secrets, unsafe APIs, and static vulnerabilities"),
    ("test_coverage_agent", "Test-Coverage Agent", "Discovers test mappings and missing test scenarios"),
    ("reviewer_manager", "Reviewer Manager", "Orchestrates fan-out/fan-in, deduplicates, ranks, and decides"),
    ("fix_suggestion_agent", "Fix-Suggestion Agent", "Generates validated unified diff patch for top finding"),
]


class SharedChangeStateModel(BaseModel):
    """Serializable snapshot of the Shared Change State."""

    review_id: str = Field(default_factory=lambda: str(uuid4()))
    overall_status: Literal["pending", "running", "completed", "failed"] = "pending"
    phase: str = "queued"
    submission_metadata: SubmissionMetadata
    files: list[SubmittedFile] = Field(default_factory=list)
    git_diff: Optional[str] = None
    agent_statuses: dict[str, AgentStatusRecord] = Field(default_factory=dict)
    agent_findings: dict[str, list[Finding]] = Field(default_factory=dict)
    agent_outputs: dict[str, dict[str, Any]] = Field(default_factory=dict)
    severity_summary: dict[str, int] = Field(
        default_factory=lambda: {
            Severity.CRITICAL.value: 0,
            Severity.HIGH.value: 0,
            Severity.MEDIUM.value: 0,
            Severity.LOW.value: 0,
            Severity.INFO.value: 0,
        }
    )
    consolidated_findings: list[Finding] = Field(default_factory=list)
    merge_recommendation: Optional[MergeRecommendation] = None
    fix_suggestion: Optional[FixSuggestion] = None
    execution_timestamps: ExecutionTimestamps = Field(default_factory=ExecutionTimestamps)
    events: list[ExecutionEvent] = Field(default_factory=list)


class SharedChangeState:
    """Thread/async-safe Shared Change State container with live subscriber support."""

    def __init__(
        self,
        submission_metadata: SubmissionMetadata,
        files: list[SubmittedFile],
        git_diff: Optional[str] = None,
        review_id: Optional[str] = None,
        event_sink: Optional[Callable[[ExecutionEvent], None]] = None,
    ) -> None:
        statuses: dict[str, AgentStatusRecord] = {}
        findings_map: dict[str, list[Finding]] = {}
        outputs_map: dict[str, dict[str, Any]] = {}

        for key, display_name, role in AGENT_DEFINITIONS:
            statuses[key] = AgentStatusRecord(
                agent_name=key,
                display_name=display_name,
                role=role,
            )
            findings_map[key] = []
            outputs_map[key] = {}

        self.data = SharedChangeStateModel(
            review_id=review_id or str(uuid4()),
            submission_metadata=submission_metadata,
            files=files,
            git_diff=git_diff,
            agent_statuses=statuses,
            agent_findings=findings_map,
            agent_outputs=outputs_map,
        )
        self._lock = asyncio.Lock()
        self._subscribers: list[asyncio.Queue[dict[str, Any]]] = []
        self._event_sink = event_sink

    @property
    def review_id(self) -> str:
        return self.data.review_id

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Register a queue to receive real-time state updates."""
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove a live subscriber queue."""
        if q in self._subscribers:
            self._subscribers.remove(q)

    def _broadcast(self, payload: dict[str, Any]) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(payload)
            except Exception:
                pass

    def _record_event(
        self,
        agent_name: str,
        event: str,
        status: str,
        findings_count: int = 0,
        message: str = "",
        error: Optional[str] = None,
    ) -> ExecutionEvent:
        ev = ExecutionEvent(
            timestamp=utc_now_iso(),
            review_id=self.data.review_id,
            agent_name=agent_name,
            event=event,
            status=status,
            findings_count=findings_count,
            message=message,
            error=error,
        )
        self.data.events.append(ev)
        if self._event_sink is not None:
            try:
                self._event_sink(ev)
            except Exception:
                pass
        return ev

    async def mark_workflow_started(self) -> None:
        async with self._lock:
            self.data.overall_status = "running"
            self.data.phase = "fan_out_specialists"
            self.data.execution_timestamps.started_at = utc_now_iso()
            ev = self._record_event(
                agent_name="reviewer_manager",
                event="workflow_started",
                status="running",
                message="Reviewer Manager initialized shared change state and started fan-out.",
            )
            self._broadcast({"type": "status_update", "status": self.to_status_response().model_dump(), "event": ev.model_dump()})

    async def mark_fan_out_started(self) -> None:
        async with self._lock:
            self.data.execution_timestamps.fan_out_started_at = utc_now_iso()
            self.data.phase = "fan_out_specialists"
            ev = self._record_event(
                agent_name="reviewer_manager",
                event="fan_out_started",
                status="running",
                message="Dispatched Diff, Style, Security, and Test-Coverage agents in parallel.",
            )
            self._broadcast({"type": "status_update", "status": self.to_status_response().model_dump(), "event": ev.model_dump()})

    async def mark_fan_in_completed(self) -> None:
        async with self._lock:
            self.data.execution_timestamps.fan_in_completed_at = utc_now_iso()
            self.data.phase = "fan_in_consolidation"
            ev = self._record_event(
                agent_name="reviewer_manager",
                event="fan_in_completed",
                status="running",
                message="Collected specialist agent results through fan-in.",
            )
            self._broadcast({"type": "status_update", "status": self.to_status_response().model_dump(), "event": ev.model_dump()})

    async def mark_agent_running(self, agent_name: str, activity: str) -> None:
        async with self._lock:
            rec = self.data.agent_statuses[agent_name]
            rec.status = AgentExecutionState.RUNNING
            rec.current_activity = activity
            if rec.started_at is None:
                rec.started_at = utc_now_iso()
            ev = self._record_event(
                agent_name=agent_name,
                event="agent_started",
                status="running",
                message=activity,
            )
            self._broadcast({"type": "status_update", "status": self.to_status_response().model_dump(), "event": ev.model_dump()})

    async def update_agent_activity(self, agent_name: str, activity: str, tool_name: Optional[str] = None) -> None:
        async with self._lock:
            rec = self.data.agent_statuses[agent_name]
            rec.current_activity = activity
            if tool_name and tool_name not in rec.tools_invoked:
                rec.tools_invoked.append(tool_name)
            ev = self._record_event(
                agent_name=agent_name,
                event="agent_progress",
                status=rec.status.value,
                findings_count=rec.findings_count,
                message=activity,
            )
            self._broadcast({"type": "status_update", "status": self.to_status_response().model_dump(), "event": ev.model_dump()})

    async def mark_agent_completed(
        self,
        agent_name: str,
        findings: list[Finding],
        output_data: dict[str, Any],
        summary: str,
        tools_invoked: Optional[list[str]] = None,
    ) -> None:
        async with self._lock:
            rec = self.data.agent_statuses[agent_name]
            now_iso = utc_now_iso()
            rec.status = AgentExecutionState.COMPLETED
            rec.completed_at = now_iso
            rec.current_activity = "Completed"
            rec.summary = summary
            rec.findings_count = len(findings)
            if tools_invoked:
                for t in tools_invoked:
                    if t not in rec.tools_invoked:
                        rec.tools_invoked.append(t)
            if rec.started_at:
                try:
                    t0 = datetime.fromisoformat(rec.started_at)
                    t1 = datetime.fromisoformat(now_iso)
                    rec.duration_ms = max(1, int((t1 - t0).total_seconds() * 1000))
                except Exception:
                    rec.duration_ms = None

            self.data.agent_findings[agent_name] = list(findings)
            self.data.agent_outputs[agent_name] = dict(output_data)

            ev = self._record_event(
                agent_name=agent_name,
                event="agent_completed",
                status="completed",
                findings_count=len(findings),
                message=summary,
            )
            self._broadcast({"type": "status_update", "status": self.to_status_response().model_dump(), "event": ev.model_dump()})

    async def mark_agent_failed(self, agent_name: str, error_message: str) -> None:
        async with self._lock:
            rec = self.data.agent_statuses[agent_name]
            now_iso = utc_now_iso()
            rec.status = AgentExecutionState.FAILED
            rec.completed_at = now_iso
            rec.current_activity = "Failed"
            rec.error = error_message
            rec.summary = f"Agent execution failed: {error_message}"
            if rec.started_at:
                try:
                    t0 = datetime.fromisoformat(rec.started_at)
                    t1 = datetime.fromisoformat(now_iso)
                    rec.duration_ms = max(1, int((t1 - t0).total_seconds() * 1000))
                except Exception:
                    rec.duration_ms = None

            ev = self._record_event(
                agent_name=agent_name,
                event="agent_failed",
                status="failed",
                findings_count=0,
                message=rec.summary,
                error=error_message,
            )
            self._broadcast({"type": "status_update", "status": self.to_status_response().model_dump(), "event": ev.model_dump()})

    async def set_consolidated_review(
        self,
        consolidated_findings: list[Finding],
        severity_summary: dict[str, int],
        merge_recommendation: MergeRecommendation,
    ) -> None:
        async with self._lock:
            self.data.consolidated_findings = list(consolidated_findings)
            self.data.severity_summary = dict(severity_summary)
            self.data.merge_recommendation = merge_recommendation
            self.data.phase = "fix_suggestion"
            self._broadcast({"type": "status_update", "status": self.to_status_response().model_dump()})

    async def set_fix_suggestion(self, fix_suggestion: FixSuggestion) -> None:
        async with self._lock:
            self.data.fix_suggestion = fix_suggestion

    async def mark_workflow_completed(self, failed: bool = False, error: Optional[str] = None) -> None:
        async with self._lock:
            now_iso = utc_now_iso()
            self.data.overall_status = "failed" if failed else "completed"
            self.data.phase = "failed" if failed else "completed"
            self.data.execution_timestamps.completed_at = now_iso
            if self.data.execution_timestamps.started_at:
                try:
                    t0 = datetime.fromisoformat(self.data.execution_timestamps.started_at)
                    t1 = datetime.fromisoformat(now_iso)
                    self.data.execution_timestamps.total_duration_ms = max(
                        1, int((t1 - t0).total_seconds() * 1000)
                    )
                except Exception:
                    pass
            ev = self._record_event(
                agent_name="reviewer_manager",
                event="workflow_failed" if failed else "workflow_completed",
                status=self.data.overall_status,
                findings_count=len(self.data.consolidated_findings),
                message=error or "Multi-agent review pipeline completed.",
                error=error,
            )
            self._broadcast({"type": "workflow_done", "status": self.to_status_response().model_dump(), "event": ev.model_dump()})

    def to_status_response(self) -> ReviewStatusResponse:
        return ReviewStatusResponse(
            review_id=self.data.review_id,
            overall_status=self.data.overall_status,
            phase=self.data.phase,
            demo_mode=self.data.submission_metadata.demo_mode,
            agent_statuses=self.data.agent_statuses,
            timestamps=self.data.execution_timestamps,
        )

    def to_detail_response(self) -> ReviewDetailResponse:
        return ReviewDetailResponse(
            review_id=self.data.review_id,
            overall_status=self.data.overall_status,
            submission_metadata=self.data.submission_metadata,
            files=self.data.files,
            git_diff=self.data.git_diff,
            agent_statuses=self.data.agent_statuses,
            agent_findings=self.data.agent_findings,
            agent_outputs=self.data.agent_outputs,
            severity_summary=self.data.severity_summary,
            consolidated_findings=self.data.consolidated_findings,
            merge_recommendation=self.data.merge_recommendation,
            fix_suggestion=self.data.fix_suggestion,
            execution_timestamps=self.data.execution_timestamps,
            events=self.data.events,
        )

