from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class QuestionOptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    content_html: str
    order_index: int


class QuestionRead(BaseModel):
    id: int
    type: str
    stem_html: str
    material_html: str | None
    answer_mode: str
    standard_answer_json: Any | None
    explanation_html: str | None
    score: float
    difficulty: str | None
    knowledge_points: list[str] | None
    version: int
    options: list[QuestionOptionRead]
