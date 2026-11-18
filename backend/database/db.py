"""SQLite database engine, session management, and repository helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base, ReviewRecord
from orchestration.schemas import (
    MergeDecision,
    ReviewDetailResponse,
    ReviewSummaryItem,
    Severity,
    utc_now_iso,
)
from orchestration.state import SharedChangeStateModel


def _get_database_url() -> str:
    env_url = os.getenv("DATABASE_URL", "").strip()
    if env_url:
        return env_url
    db_path = Path(__file__).resolve().parent.parent / "code_review_board.db"
    return f"sqlite:///{db_path.as_posix()}"


_DATABASE_URL = _get_database_url()
_CONNECT_ARGS = {"check_same_thread": False} if _DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(_DATABASE_URL, connect_args=_CONNECT_ARGS, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    """Create SQLite tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def save_review_state(detail: ReviewDetailResponse, db_session: Optional[Session] = None) -> None:
    """Insert or update a ReviewRecord from a ReviewDetailResponse."""
    owns_session = db_session is None
    session = db_session or SessionLocal()
    try:
        sev = detail.severity_summary
        rec = session.get(ReviewRecord, detail.review_id)
        payload_json = detail.model_dump_json()
        merge_val = detail.merge_recommendation.decision.value if detail.merge_recommendation else None
        patch_approved = bool(detail.fix_suggestion and detail.fix_suggestion.user_approved)

        if rec is None:
            rec = ReviewRecord(
                review_id=detail.review_id,
                title=detail.submission_metadata.title,
                description=detail.submission_metadata.description,
                submission_type=detail.submission_metadata.submission_type,
                status=detail.overall_status,
                merge_recommendation=merge_val,
                demo_mode=detail.submission_metadata.demo_mode,
                critical_count=sev.get(Severity.CRITICAL.value, 0),
                high_count=sev.get(Severity.HIGH.value, 0),
                medium_count=sev.get(Severity.MEDIUM.value, 0),
                low_count=sev.get(Severity.LOW.value, 0),
                info_count=sev.get(Severity.INFO.value, 0),
                total_findings=len(detail.consolidated_findings),
                patch_approved=patch_approved,
                created_at=detail.submission_metadata.created_at,
                completed_at=detail.execution_timestamps.completed_at,
                duration_ms=detail.execution_timestamps.total_duration_ms,
                state_json=payload_json,
            )
            session.add(rec)
        else:
            rec.title = detail.submission_metadata.title
            rec.description = detail.submission_metadata.description
            rec.status = detail.overall_status
            rec.merge_recommendation = merge_val
            rec.demo_mode = detail.submission_metadata.demo_mode
            rec.critical_count = sev.get(Severity.CRITICAL.value, 0)
            rec.high_count = sev.get(Severity.HIGH.value, 0)
            rec.medium_count = sev.get(Severity.MEDIUM.value, 0)
            rec.low_count = sev.get(Severity.LOW.value, 0)
            rec.info_count = sev.get(Severity.INFO.value, 0)
            rec.total_findings = len(detail.consolidated_findings)
            rec.patch_approved = patch_approved
            rec.completed_at = detail.execution_timestamps.completed_at
            rec.duration_ms = detail.execution_timestamps.total_duration_ms
            rec.state_json = payload_json

        session.commit()
    finally:
        if owns_session:
            session.close()


def list_reviews(db_session: Optional[Session] = None) -> list[ReviewSummaryItem]:
    """List all reviews ordered newest first."""
    owns_session = db_session is None
    session = db_session or SessionLocal()
    try:
        rows = session.query(ReviewRecord).order_by(ReviewRecord.created_at.desc()).all()
        items: list[ReviewSummaryItem] = []
        for r in rows:
            merge_dec = MergeDecision(r.merge_recommendation) if r.merge_recommendation else None
            items.append(
                ReviewSummaryItem(
                    review_id=r.review_id,
                    title=r.title,
                    description=r.description,
                    submission_type=r.submission_type,
                    status=r.status,
                    merge_recommendation=merge_dec,
                    demo_mode=r.demo_mode,
                    critical_count=r.critical_count,
                    high_count=r.high_count,
                    medium_count=r.medium_count,
                    low_count=r.low_count,
                    info_count=r.info_count,
                    total_findings=r.total_findings,
                    patch_approved=bool(r.patch_approved),
                    created_at=r.created_at,
                    completed_at=r.completed_at,
                    duration_ms=r.duration_ms,
                )
            )
        return items
    finally:
        if owns_session:
            session.close()


def get_review_detail(review_id: str, db_session: Optional[Session] = None) -> Optional[ReviewDetailResponse]:
    """Fetch complete persisted ReviewDetailResponse by review_id."""
    owns_session = db_session is None
    session = db_session or SessionLocal()
    try:
        rec = session.get(ReviewRecord, review_id)
        if rec is None:
            return None
        return ReviewDetailResponse.model_validate_json(rec.state_json)
    finally:
        if owns_session:
            session.close()


def approve_review_patch(review_id: str, db_session: Optional[Session] = None) -> Optional[ReviewDetailResponse]:
    """Record explicit user approval on a review's FixSuggestion."""
    owns_session = db_session is None
    session = db_session or SessionLocal()
    try:
        rec = session.get(ReviewRecord, review_id)
        if rec is None:
            return None
        detail = ReviewDetailResponse.model_validate_json(rec.state_json)
        if detail.fix_suggestion and detail.fix_suggestion.available:
            detail.fix_suggestion.user_approved = True
            detail.fix_suggestion.approved_at = utc_now_iso()
            rec.patch_approved = True
            rec.state_json = detail.model_dump_json()
            session.commit()
        return detail
    finally:
        if owns_session:
            session.close()


def delete_review(review_id: str, db_session: Optional[Session] = None) -> bool:
    """Delete a review record from SQLite."""
    owns_session = db_session is None
    session = db_session or SessionLocal()
    try:
        rec = session.get(ReviewRecord, review_id)
        if rec is None:
            return False
        session.delete(rec)
        session.commit()
        return True
    finally:
        if owns_session:
            session.close()


def get_dashboard_stats(db_session: Optional[Session] = None) -> dict[str, Any]:
    """Compute real aggregated review and agent execution statistics from SQLite."""
    owns_session = db_session is None
    session = db_session or SessionLocal()
    try:
        rows = session.query(ReviewRecord).order_by(ReviewRecord.created_at.desc()).all()
        total_reviews = len(rows)
        approved_reviews = sum(1 for r in rows if r.merge_recommendation == MergeDecision.APPROVE.value)
        changes_requested = sum(1 for r in rows if r.merge_recommendation == MergeDecision.REQUEST_CHANGES.value)
        patches_approved = sum(1 for r in rows if r.patch_approved)
        critical_detected = sum(r.critical_count for r in rows)
        open_critical = max(0, critical_detected - patches_approved)

        agent_agg: dict[str, dict[str, Any]] = {}
        for r in rows:
            try:
                data = json.loads(r.state_json)
                statuses = data.get("agent_statuses", {})
                for agent_key, st in statuses.items():
                    bucket = agent_agg.setdefault(
                        agent_key,
                        {
                            "agent_name": agent_key,
                            "display_name": st.get("display_name", agent_key),
                            "runs": 0,
                            "completed": 0,
                            "failed": 0,
                            "total_duration_ms": 0,
                            "total_findings": 0,
                        },
                    )
                    bucket["runs"] += 1
                    if st.get("status") == "completed":
                        bucket["completed"] += 1
                    elif st.get("status") == "failed":
                        bucket["failed"] += 1
                    if isinstance(st.get("duration_ms"), int):
                        bucket["total_duration_ms"] += st["duration_ms"]
                    bucket["total_findings"] += int(st.get("findings_count", 0))
            except Exception:
                continue

        agent_stats = []
        for bucket in agent_agg.values():
            runs = max(1, bucket["runs"])
            agent_stats.append(
                {
                    "agent_name": bucket["agent_name"],
                    "display_name": bucket["display_name"],
                    "runs": bucket["runs"],
                    "completed": bucket["completed"],
                    "failed": bucket["failed"],
                    "avg_duration_ms": round(bucket["total_duration_ms"] / runs),
                    "total_findings": bucket["total_findings"],
                }
            )

        return {
            "total_reviews": total_reviews,
            "approved_reviews": approved_reviews,
            "changes_requested": changes_requested,
            "critical_issues_detected": open_critical,
            "total_critical_detected": critical_detected,
            "patches_approved": patches_approved,
            "agent_stats": agent_stats,
        }
    finally:
        if owns_session:
            session.close()

