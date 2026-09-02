from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WrongQuestion(Base):
    __tablename__ = "wrong_questions"
    __table_args__ = (UniqueConstraint("user_id", "question_id", name="uq_wrong_user_question"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, default=1, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    state: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    wrong_count: Mapped[int] = mapped_column(Integer, default=1)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_review_count: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_correct_count: Mapped[int] = mapped_column(Integer, default=0)
    first_wrong_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_wrong_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_review_at: Mapped[datetime | None] = mapped_column(nullable=True)
    mastered_at: Mapped[datetime | None] = mapped_column(nullable=True)


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "question_id", name="uq_favorite_user_question"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, default=1, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
