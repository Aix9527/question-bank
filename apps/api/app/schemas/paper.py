from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.question import QuestionRead


class PaperListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_id: int
    title: str
    paper_type: str
    total_score: float | None
    time_limit_minutes: int | None
    status: str
    version: int


class PaperSectionRead(BaseModel):
    id: int
    title: str
    order_index: int
    instruction: str | None
    score_total: float | None
    questions: list[QuestionRead]


class PaperDetail(BaseModel):
    id: int
    subject_id: int
    title: str
    paper_type: str
    total_score: float | None
    time_limit_minutes: int | None
    status: str
    version: int
    sections: list[PaperSectionRead]
