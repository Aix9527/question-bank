from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ImportJob(Base):
    __tablename__ = 'import_jobs'
    __table_args__ = (UniqueConstraint('source_sha256', 'subject_code', name='uq_import_source_subject'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_code: Mapped[str] = mapped_column(String(32), index=True)
    source_filename: Mapped[str] = mapped_column(String(512))
    source_sha256: Mapped[str] = mapped_column(String(64), index=True)
    source_size: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default='pending_review', index=True)
    ast_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    draft_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    warnings_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    review_revision: Mapped[int] = mapped_column(Integer, default=1)
    published_paper_id: Mapped[int | None] = mapped_column(ForeignKey('papers.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
