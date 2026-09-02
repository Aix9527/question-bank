from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ManualReviewSubmit(BaseModel):
    suggested_score: float | None = None
    final_score: float
    comment: str | None = None
    rubric_json: dict[str, Any] | list[Any] | None = None


class ManualReviewRead(BaseModel):
    id: int
    answer_id: int
    attempt_id: int
    question_id: int
    status: str
    suggested_score: float | None
    final_score: float | None
    comment: str | None
    rubric_json: Any | None
    reviewer_user_id: int | None
    created_at: datetime
    reviewed_at: datetime | None
    max_score: float
    answer_json: Any | None
    ai_suggestion: dict[str, Any] | None = None
    question: dict[str, Any]
