from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ContentStatus = Literal['draft', 'published', 'archived']


class OptionWrite(BaseModel):
    label: str = Field(min_length=1, max_length=16)
    content_html: str
    order_index: int = Field(ge=1)


class QuestionCreate(BaseModel):
    subject_code: Literal['chinese', 'math', 'english']
    type: str = Field(min_length=1, max_length=64)
    stem_html: str = Field(min_length=1)
    material_html: str | None = None
    answer_mode: str = Field(default='manual', min_length=1, max_length=64)
    standard_answer_json: Any | None = None
    explanation_html: str | None = None
    score: float = Field(default=0, ge=0)
    difficulty: str | None = None
    knowledge_points: list[str] | None = None
    source: str | None = None
    status: ContentStatus = 'draft'
    options: list[OptionWrite] = Field(default_factory=list)


class QuestionUpdate(BaseModel):
    type: str | None = Field(default=None, min_length=1, max_length=64)
    stem_html: str | None = Field(default=None, min_length=1)
    material_html: str | None = None
    answer_mode: str | None = Field(default=None, min_length=1, max_length=64)
    standard_answer_json: Any | None = None
    explanation_html: str | None = None
    score: float | None = Field(default=None, ge=0)
    difficulty: str | None = None
    knowledge_points: list[str] | None = None
    source: str | None = None
    status: ContentStatus | None = None
    options: list[OptionWrite] | None = None


class QuestionAdminRead(BaseModel):
    id: int
    subject_id: int
    subject_code: str
    type: str
    stem_html: str
    material_html: str | None
    answer_mode: str
    standard_answer_json: Any | None
    explanation_html: str | None
    score: float
    difficulty: str | None
    knowledge_points: list[str] | None
    source: str | None
    status: str
    version: int
    options: list[dict[str, Any]]


class PaperCreate(BaseModel):
    subject_code: Literal['chinese', 'math', 'english']
    title: str = Field(min_length=1, max_length=255)
    source_file: str | None = None
    paper_type: str = Field(default='mock', min_length=1, max_length=32)
    total_score: float | None = Field(default=None, ge=0)
    time_limit_minutes: int | None = Field(default=None, ge=1)
    status: ContentStatus = 'draft'


class PaperUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    source_file: str | None = None
    paper_type: str | None = Field(default=None, min_length=1, max_length=32)
    total_score: float | None = Field(default=None, ge=0)
    time_limit_minutes: int | None = Field(default=None, ge=1)
    status: ContentStatus | None = None


class PaperAdminRead(BaseModel):
    id: int
    subject_id: int
    subject_code: str
    title: str
    source_file: str | None
    paper_type: str
    total_score: float | None
    time_limit_minutes: int | None
    status: str
    version: int
    section_count: int
    question_count: int
