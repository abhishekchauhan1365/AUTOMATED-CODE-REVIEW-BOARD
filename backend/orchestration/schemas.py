"""Pydantic schemas for the Automated Code Review Board."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


class Severity(str, Enum):
    """Normalized severity levels ordered from highest to lowest."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


SEVERITY_ORDER: dict[Severity, int] = {
    Severity.CRITICAL: 5,
    Severity.HIGH: 4,
    Severity.MEDIUM: 3,
    Severity.LOW: 2,
    Severity.INFO: 1,
}


class MergeDecision(str, Enum):
    """Final merge recommendations produced by the Reviewer Manager."""

    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"


class AgentExecutionState(str, Enum):
    """Lifecycle states for each agent in the workflow."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SubmittedFile(BaseModel):
    """Represents a single source or test file submitted for review."""

    path: str
    language: str = "text"
    content: str = ""
    size_bytes: int = 0
    status: Literal["added", "modified", "deleted"] = "modified"


class SubmissionMetadata(BaseModel):
    """Metadata describing the review submission and runtime mode."""

    title: str = "Code Review Submission"
    description: str = ""
    submission_type: Literal["files", "diff"] = "files"
    created_at: str = Field(default_factory=utc_now_iso)
    llm_provider: str = "groq"
    model_used: str = "llama-3.3-70b-versatile"
    demo_mode: bool = False


class Finding(BaseModel):
    """Structured code review finding emitted by an agent."""

    id: str
    title: str
    description: str
    severity: Severity
    agent: str
    category: str = "general"
    file_path: str = "unknown"
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    evidence: str = ""
    recommended_action: str = ""
    rule_id: Optional[str] = None
    source: Literal["deterministic_tool", "llm_analysis", "hybrid", "demo_mode"] = "hybrid"
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    corroborated_by: list[str] = Field(default_factory=list)


class AgentStatusRecord(BaseModel):
    """Live execution status for one of the six agents."""

    agent_name: str
    display_name: str
    role: str
    status: AgentExecutionState = AgentExecutionState.PENDING
    current_activity: str = "Waiting to start"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    findings_count: int = 0
    summary: str = ""
    error: Optional[str] = None
    tools_invoked: list[str] = Field(default_factory=list)


class MergeRecommendation(BaseModel):
    """Consolidated merge decision and justification."""

    decision: MergeDecision
    reasoning: str
    decision_factors: list[str] = Field(default_factory=list)
    blocking_findings_count: int = 0
    has_agent_failures: bool = False


class FixSuggestion(BaseModel):
    """Output produced by the Fix-Suggestion Agent."""

    available: bool = False
    selected_finding: Optional[Finding] = None
    file_path: str = ""
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    original_code: str = ""
    suggested_replacement: str = ""
    explanation: str = ""
    proposed_patch: str = ""
    validation_status: Literal["valid", "invalid", "unavailable"] = "unavailable"
    validation_message: str = ""
    requires_explicit_approval: bool = True
    user_approved: bool = False
    approved_at: Optional[str] = None
    safety_note: str = (
        "Patch has NOT been executed or applied to original files. "
        "Explicit user approval is required before downloading or applying."
    )


class ExecutionTimestamps(BaseModel):
    """Timestamps across workflow stages."""

    submitted_at: str = Field(default_factory=utc_now_iso)
    started_at: Optional[str] = None
    fan_out_started_at: Optional[str] = None
    fan_in_completed_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_duration_ms: Optional[int] = None


class ExecutionEvent(BaseModel):
    """Append-only execution trace event."""

    timestamp: str = Field(default_factory=utc_now_iso)
    review_id: str
    agent_name: str
    event: str
    status: str
    findings_count: int = 0
    message: str = ""
    error: Optional[str] = None


class ReviewCreateRequest(BaseModel):
    """JSON body payload for POST /api/reviews."""

    title: Optional[str] = None
    description: str = ""
    submission_type: Literal["files", "diff"] = "diff"
    git_diff: Optional[str] = None
    files: list[dict[str, Any]] = Field(default_factory=list)
    demo_mode: Optional[bool] = None


class ReviewStatusResponse(BaseModel):
    """Response schema for GET /api/reviews/{review_id}/status."""

    review_id: str
    overall_status: Literal["pending", "running", "completed", "failed"]
    phase: str
    demo_mode: bool
    agent_statuses: dict[str, AgentStatusRecord]
    timestamps: ExecutionTimestamps


class ReviewSummaryItem(BaseModel):
    """Compact summary item for Review History & Dashboard."""

    review_id: str
    title: str
    description: str
    submission_type: str
    status: str
    merge_recommendation: Optional[MergeDecision] = None
    demo_mode: bool = False
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    total_findings: int = 0
    patch_approved: bool = False
    created_at: str
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None


class ReviewDetailResponse(BaseModel):
    """Complete review result returned by GET /api/reviews/{review_id}."""

    review_id: str
    overall_status: Literal["pending", "running", "completed", "failed"]
    submission_metadata: SubmissionMetadata
    files: list[SubmittedFile]
    git_diff: Optional[str] = None
    agent_statuses: dict[str, AgentStatusRecord]
    agent_findings: dict[str, list[Finding]]
    agent_outputs: dict[str, dict[str, Any]]
    severity_summary: dict[str, int]
    consolidated_findings: list[Finding]
    merge_recommendation: Optional[MergeRecommendation] = None
    fix_suggestion: Optional[FixSuggestion] = None
    execution_timestamps: ExecutionTimestamps
    events: list[ExecutionEvent] = Field(default_factory=list)

