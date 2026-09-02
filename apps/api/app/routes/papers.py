from fastapi import APIRouter, HTTPException, Request

from app.schemas.paper import PaperDetail, PaperListItem
from app.services.paper_service import get_paper_detail, list_published_papers

router = APIRouter(tags=["papers"])


@router.get("/api/subjects/{subject_code}/papers", response_model=list[PaperListItem])
def subject_papers(subject_code: str, request: Request):
    with request.app.state.session_factory() as session:
        return list_published_papers(session, subject_code)


@router.get("/api/papers/{paper_id}", response_model=PaperDetail)
def paper_detail(paper_id: int, request: Request):
    with request.app.state.session_factory() as session:
        paper = get_paper_detail(session, paper_id)
        if paper is None:
            raise HTTPException(status_code=404, detail="paper not found")
        return paper
