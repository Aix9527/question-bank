from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    source_file: Mapped[str | None] = mapped_column(String(512), nullable=True)
    paper_type: Mapped[str] = mapped_column(String(32), default="mock")
    total_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    sections: Mapped[list["PaperSection"]] = relationship(back_populates="paper", cascade="all, delete-orphan")


class PaperSection(Base):
    __tablename__ = "paper_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    order_index: Mapped[int] = mapped_column(Integer)
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    score_total: Mapped[float | None] = mapped_column(Float, nullable=True)

    paper: Mapped[Paper] = relationship(back_populates="sections")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    type: Mapped[str] = mapped_column(String(64), index=True)
    stem_html: Mapped[str] = mapped_column(Text)
    material_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_mode: Mapped[str] = mapped_column(String(64), default="manual")
    standard_answer_json: Mapped[dict[str, Any] | list[Any] | str | int | float | None] = mapped_column(JSON, nullable=True)
    explanation_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0)
    difficulty: Mapped[str | None] = mapped_column(String(32), nullable=True)
    knowledge_points: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    options: Mapped[list["QuestionOption"]] = relationship(back_populates="question", cascade="all, delete-orphan")


class QuestionOption(Base):
    __tablename__ = "question_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(16))
    content_html: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer)

    question: Mapped[Question] = relationship(back_populates="options")


class PaperQuestion(Base):
    __tablename__ = "paper_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("paper_sections.id", ondelete="CASCADE"), index=True)
    order_index: Mapped[int] = mapped_column(Integer)
    score_override: Mapped[float | None] = mapped_column(Float, nullable=True)
