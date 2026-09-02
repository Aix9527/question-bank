from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class LearningQuestion(BaseModel):
    id: int
    subject_id: int
    type: str
    stem_html: str
    material_html: str | None
    answer_mode: str
    explanation_html: str | None
    score: float
    difficulty: str | None
    knowledge_points: list[str] | None
    options: list[dict[str, Any]]


class WrongQuestionRead(BaseModel):
    id: int
    question_id: int
    state: str
    wrong_count: int
    review_count: int
    correct_review_count: int
    consecutive_correct_count: int
    first_wrong_at: datetime
    last_wrong_at: datetime
    last_review_at: datetime | None
    mastered_at: datetime | None
    question: LearningQuestion


class FavoriteRead(BaseModel):
    id: int
    question_id: int
    created_at: datetime
    question: LearningQuestion


class ReviewAttemptCreate(BaseModel):
    question_ids: list[int] | None = None


class ReviewAttemptRead(BaseModel):
    attempt: dict[str, Any]
    question_ids: list[int]
