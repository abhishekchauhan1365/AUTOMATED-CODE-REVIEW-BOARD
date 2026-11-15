"""SQLAlchemy ORM models for persistent review history."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarative class."""


class ReviewRecord(Base):
    """Persisted code review summary and full serialized SharedChangeState."""

    __tablename__ = "reviews"

    review_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    submission_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    merge_recommendation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    demo_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    critical_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    high_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    medium_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    info_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_findings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    patch_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    completed_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state_json: Mapped[str] = mapped_column(Text, nullable=False)

