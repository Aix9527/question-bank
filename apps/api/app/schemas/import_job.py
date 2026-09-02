from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ImportJobSummary(BaseModel):
    id: int
    subject_code: str
    source_filename: str
    source_sha256: str
    source_size: int
    title: str
    status: str
    blocking_warning_count: int
    warning_count: int
    published_paper_id: int | None = None
    reused: bool = False


class ImportReview(BaseModel):
    id: int
    subject_code: str
    source_filename: str
    source_sha256: str
    status: str
    review_revision: int
    draft: dict[str, Any]
    warnings: list[dict[str, Any]]
    blocking_warning_count: int


class ImportReviewUpdate(BaseModel):
    draft: dict[str, Any]
    resolve_warning_ids: list[str] = Field(default_factory=list)
    resolution_note: str | None = None


class ImportPublishResult(BaseModel):
    id: int
    status: str
    paper_id: int | None
