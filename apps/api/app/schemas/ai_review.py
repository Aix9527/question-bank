from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AIReviewSuggestionRead(BaseModel):
    id: int
    answer_id: int
    provider: str
    model: str | None
    version: int
    suggested_score: float
    confidence: str
    comment: str
    strengths: list[str]
    improvements: list[str]
    rubric: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
