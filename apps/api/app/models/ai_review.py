from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AIReviewSuggestion(Base):
    __tablename__ = 'ai_review_suggestions'
    __table_args__ = (UniqueConstraint('answer_id', name='uq_ai_review_answer'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    answer_id: Mapped[int] = mapped_column(ForeignKey('answer_records.id', ondelete='CASCADE'), index=True)
    provider: Mapped[str] = mapped_column(String(32), default='openai')
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    suggested_score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String(16), default='medium')
    comment: Mapped[str] = mapped_column(Text)
    strengths_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    improvements_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    rubric_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
