from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.models.question_bank import Paper, Question
from app.schemas.admin_content import (
    PaperAdminRead,
    PaperCreate,
    PaperUpdate,
    QuestionAdminRead,
    QuestionCreate,
    QuestionUpdate,
)
from app.services.admin_content import (
    archive_paper,
    archive_question,
    create_paper,
    create_question,
    list_papers,
    list_questions,
    paper_payload,
    question_payload,
    update_paper,
    update_question,
)

router = APIRouter(prefix='/api/admin', tags=['admin-content'])


@router.get('/questions', response_model=list[QuestionAdminRead])
def admin_questions(
    request: Request,
    subject_code: str | None = None,
    status_filter: str | None = Query(default=None, alias='status'),
    question_type: str | None = Query(default=None, alias='type'),
    limit: int = Query(default=200, ge=1, le=1000),
):
    with request.app.state.session_factory() as session:
        return list_questions(
            session,
            subject_code=subject_code,
            status=status_filter,
            question_type=question_type,
            limit=limit,
        )


@router.post('/questions', response_model=QuestionAdminRead, status_code=status.HTTP_201_CREATED)
def admin_create_question(payload: QuestionCreate, request: Request):
    with request.app.state.session_factory() as session:
        question = create_question(session, payload.model_dump())
        if question is None:
            raise HTTPException(status_code=400, detail='unknown subject')
        return question_payload(session, question)


@router.get('/questions/{question_id}', response_model=QuestionAdminRead)
def admin_question(question_id: int, request: Request):
    with request.app.state.session_factory() as session:
        question = session.get(Question, question_id)
        if question is None:
            raise HTTPException(status_code=404, detail='question not found')
        return question_payload(session, question)


@router.patch('/questions/{question_id}', response_model=QuestionAdminRead)
def admin_update_question(question_id: int, payload: QuestionUpdate, request: Request):
    with request.app.state.session_factory() as session:
        question = session.get(Question, question_id)
        if question is None:
            raise HTTPException(status_code=404, detail='question not found')
        question = update_question(session, question, payload.model_dump(exclude_unset=True))
        return question_payload(session, question)


@router.delete('/questions/{question_id}', response_model=QuestionAdminRead)
def admin_archive_question(question_id: int, request: Request):
    with request.app.state.session_factory() as session:
        question = session.get(Question, question_id)
        if question is None:
            raise HTTPException(status_code=404, detail='question not found')
        question = archive_question(session, question)
        return question_payload(session, question)


@router.get('/papers', response_model=list[PaperAdminRead])
def admin_papers(
    request: Request,
    subject_code: str | None = None,
    status_filter: str | None = Query(default=None, alias='status'),
):
    with request.app.state.session_factory() as session:
        return list_papers(session, subject_code=subject_code, status=status_filter)


@router.post('/papers', response_model=PaperAdminRead, status_code=status.HTTP_201_CREATED)
def admin_create_paper(payload: PaperCreate, request: Request):
    with request.app.state.session_factory() as session:
        paper = create_paper(session, payload.model_dump())
        if paper is None:
            raise HTTPException(status_code=400, detail='unknown subject')
        return paper_payload(session, paper)


@router.get('/papers/{paper_id}', response_model=PaperAdminRead)
def admin_paper(paper_id: int, request: Request):
    with request.app.state.session_factory() as session:
        paper = session.get(Paper, paper_id)
        if paper is None:
            raise HTTPException(status_code=404, detail='paper not found')
        return paper_payload(session, paper)


@router.patch('/papers/{paper_id}', response_model=PaperAdminRead)
def admin_update_paper(paper_id: int, payload: PaperUpdate, request: Request):
    with request.app.state.session_factory() as session:
        paper = session.get(Paper, paper_id)
        if paper is None:
            raise HTTPException(status_code=404, detail='paper not found')
        paper = update_paper(session, paper, payload.model_dump(exclude_unset=True))
        return paper_payload(session, paper)


@router.delete('/papers/{paper_id}', response_model=PaperAdminRead)
def admin_archive_paper(paper_id: int, request: Request):
    with request.app.state.session_factory() as session:
        paper = session.get(Paper, paper_id)
        if paper is None:
            raise HTTPException(status_code=404, detail='paper not found')
        paper = archive_paper(session, paper)
        return paper_payload(session, paper)
