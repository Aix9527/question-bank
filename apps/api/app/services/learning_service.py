from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.models.learning import Favorite, WrongQuestion
from app.models.question_bank import Question, QuestionOption
from app.services.attempt_service import create_attempt, get_attempt_payload

MASTER_AFTER_CONSECUTIVE_CORRECT = 2


def _question_payload(session: Session, question: Question) -> dict:
    options = list(
        session.scalars(
            select(QuestionOption)
            .where(QuestionOption.question_id == question.id)
            .order_by(QuestionOption.order_index, QuestionOption.id)
        ).all()
    )
    return {
        "id": question.id,
        "subject_id": question.subject_id,
        "type": question.type,
        "stem_html": question.stem_html,
        "material_html": question.material_html,
        "answer_mode": question.answer_mode,
        "explanation_html": question.explanation_html,
        "score": question.score,
        "difficulty": question.difficulty,
        "knowledge_points": question.knowledge_points,
        "options": [
            {"id": option.id, "label": option.label, "content_html": option.content_html, "order_index": option.order_index}
            for option in options
        ],
    }


def update_wrong_question(
    session: Session,
    *,
    user_id: int,
    question_id: int,
    is_correct: bool,
    attempt_mode: str,
) -> None:
    now = datetime.now(timezone.utc)
    wrong = session.scalar(
        select(WrongQuestion).where(
            WrongQuestion.user_id == user_id,
            WrongQuestion.question_id == question_id,
        )
    )

    if not is_correct:
        if wrong is None:
            wrong = WrongQuestion(
                user_id=user_id,
                question_id=question_id,
                state="pending",
                wrong_count=1,
                review_count=1 if attempt_mode == "wrong_review" else 0,
                correct_review_count=0,
                consecutive_correct_count=0,
                first_wrong_at=now,
                last_wrong_at=now,
                last_review_at=now if attempt_mode == "wrong_review" else None,
            )
            session.add(wrong)
        else:
            wrong.wrong_count += 1
            wrong.state = "pending"
            wrong.last_wrong_at = now
            wrong.mastered_at = None
            wrong.consecutive_correct_count = 0
            if attempt_mode == "wrong_review":
                wrong.review_count += 1
                wrong.last_review_at = now
        return

    if attempt_mode != "wrong_review" or wrong is None:
        return

    wrong.review_count += 1
    wrong.correct_review_count += 1
    wrong.consecutive_correct_count += 1
    wrong.last_review_at = now
    if wrong.consecutive_correct_count >= MASTER_AFTER_CONSECUTIVE_CORRECT:
        wrong.state = "mastered"
        wrong.mastered_at = now
    else:
        wrong.state = "learning"
        wrong.mastered_at = None


def list_wrong_questions(session: Session, *, user_id: int = 1, include_mastered: bool = True) -> list[dict]:
    stmt = select(WrongQuestion).where(WrongQuestion.user_id == user_id)
    if not include_mastered:
        stmt = stmt.where(WrongQuestion.state != "mastered")
    rows = list(session.scalars(stmt.order_by(WrongQuestion.last_wrong_at.desc(), WrongQuestion.id.desc())).all())
    payload: list[dict] = []
    for row in rows:
        question = session.get(Question, row.question_id)
        if question is None:
            continue
        payload.append(
            {
                "id": row.id,
                "question_id": row.question_id,
                "state": row.state,
                "wrong_count": row.wrong_count,
                "review_count": row.review_count,
                "correct_review_count": row.correct_review_count,
                "consecutive_correct_count": row.consecutive_correct_count,
                "first_wrong_at": row.first_wrong_at,
                "last_wrong_at": row.last_wrong_at,
                "last_review_at": row.last_review_at,
                "mastered_at": row.mastered_at,
                "question": _question_payload(session, question),
            }
        )
    return payload


def create_wrong_review_attempt(
    session: Session,
    *,
    question_ids: list[int] | None = None,
    user_id: int = 1,
) -> dict | None:
    pending = list_wrong_questions(session, user_id=user_id, include_mastered=False)
    available_ids = [item["question_id"] for item in pending]
    if question_ids is None:
        selected = available_ids
    else:
        requested = list(dict.fromkeys(question_ids))
        if any(question_id not in available_ids for question_id in requested):
            return None
        selected = requested
    if not selected:
        return None

    first_question = session.get(Question, selected[0])
    if first_question is None:
        return None
    if any((session.get(Question, question_id) or first_question).subject_id != first_question.subject_id for question_id in selected):
        return None

    attempt = create_attempt(
        session,
        subject_id=first_question.subject_id,
        paper_id=None,
        mode="wrong_review",
        user_id=user_id,
    )
    return {"attempt": get_attempt_payload(session, attempt.id), "question_ids": selected}


def add_favorite(session: Session, *, question_id: int, user_id: int = 1) -> tuple[dict | None, bool]:
    question = session.get(Question, question_id)
    if question is None:
        return None, False
    favorite = session.scalar(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.question_id == question_id)
    )
    created = False
    if favorite is None:
        favorite = Favorite(user_id=user_id, question_id=question_id)
        session.add(favorite)
        session.commit()
        session.refresh(favorite)
        created = True
    return {
        "id": favorite.id,
        "question_id": favorite.question_id,
        "created_at": favorite.created_at,
        "question": _question_payload(session, question),
    }, created


def remove_favorite(session: Session, *, question_id: int, user_id: int = 1) -> bool:
    favorite = session.scalar(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.question_id == question_id)
    )
    if favorite is None:
        return False
    session.delete(favorite)
    session.commit()
    return True


def list_favorites(session: Session, *, user_id: int = 1) -> list[dict]:
    rows = list(
        session.scalars(
            select(Favorite)
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc(), Favorite.id.desc())
        ).all()
    )
    payload: list[dict] = []
    for row in rows:
        question = session.get(Question, row.question_id)
        if question is None:
            continue
        payload.append(
            {
                "id": row.id,
                "question_id": row.question_id,
                "created_at": row.created_at,
                "question": _question_payload(session, question),
            }
        )
    return payload
