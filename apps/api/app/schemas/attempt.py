from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AttemptCreate(BaseModel):
    subject_id: int
    paper_id: int | None = None
    mode: str = "practice"


class AnswerSave(BaseModel):
    answer_json: Any = None
    time_spent_seconds: int = 0


class AnswerRead(BaseModel):
    id: int
    question_id: int
    question_version: int
    answer_json: Any = None
    is_correct: bool | None
    auto_score: float | None
    final_score: float | None
    grading_status: str
    time_spent_seconds: int
    answered_at: datetime


class AttemptRead(BaseModel):
    id: int
    user_id: int
    subject_id: int
    paper_id: int | None
    mode: str
    status: str
    started_at: datetime
    submitted_at: datetime | None
    score: float | None
    max_score: float | None
    answers: list[AnswerRead]
