from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.schemas.attempt import AnswerRead, AnswerSave, AttemptCreate, AttemptRead
from app.security import get_current_user
from app.services.attempt_service import create_attempt, get_attempt_payload, save_answer, submit_attempt

router = APIRouter(prefix="/api/attempts", tags=["attempts"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AttemptRead)
def create_attempt_endpoint(payload: AttemptCreate, request: Request, user=Depends(get_current_user)):
    with request.app.state.session_factory() as session:
        attempt = create_attempt(
            session,
            subject_id=payload.subject_id,
            paper_id=payload.paper_id,
            mode=payload.mode,
            user_id=user.id,
        )
        return get_attempt_payload(session, attempt.id, user_id=user.id)


@router.get("/{attempt_id}", response_model=AttemptRead)
def get_attempt_endpoint(attempt_id: int, request: Request, user=Depends(get_current_user)):
    with request.app.state.session_factory() as session:
        payload = get_attempt_payload(session, attempt_id, user_id=user.id)
        if payload is None:
            raise HTTPException(status_code=404, detail="attempt not found")
        return payload


@router.patch("/{attempt_id}/answers/{question_id}", response_model=AnswerRead)
def save_answer_endpoint(attempt_id: int, question_id: int, payload: AnswerSave, request: Request, user=Depends(get_current_user)):
    if payload.answer_json is not None and not isinstance(payload.answer_json, dict):
        raise HTTPException(status_code=400, detail="answer_json must be an object or null")
    with request.app.state.session_factory() as session:
        record = save_answer(
            session,
            attempt_id=attempt_id,
            question_id=question_id,
            answer_json=payload.answer_json,
            time_spent_seconds=payload.time_spent_seconds,
            user_id=user.id,
        )
        if record is None:
            raise HTTPException(status_code=404, detail="attempt or question not found")
        return record


@router.post("/{attempt_id}/submit", response_model=AttemptRead)
def submit_attempt_endpoint(attempt_id: int, request: Request, user=Depends(get_current_user)):
    with request.app.state.session_factory() as session:
        payload = submit_attempt(session, attempt_id, user_id=user.id)
        if payload is None:
            raise HTTPException(status_code=404, detail="attempt not found")
        return payload
