from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attempt import AnswerRecord, Attempt
from app.models.question_bank import Question


def create_attempt(session: Session, *, subject_id: int, paper_id: int | None, mode: str, user_id: int = 1) -> Attempt:
    attempt = Attempt(user_id=user_id, subject_id=subject_id, paper_id=paper_id, mode=mode)
    session.add(attempt)
    session.commit()
    session.refresh(attempt)
    return attempt


def save_answer(session: Session, *, attempt_id: int, question_id: int, answer_json, time_spent_seconds: int, user_id: int | None = None) -> AnswerRecord | None:
    attempt = session.get(Attempt, attempt_id)
    question = session.get(Question, question_id)
    if attempt is None or question is None or attempt.status != "in_progress":
        return None
    if user_id is not None and attempt.user_id != user_id:
        return None
    if answer_json is not None and not isinstance(answer_json, dict):
        raise ValueError("answer_json must be an object or null")

    record = session.scalar(
        select(AnswerRecord).where(
            AnswerRecord.attempt_id == attempt_id,
            AnswerRecord.question_id == question_id,
        )
    )
    if record is None:
        record = AnswerRecord(
            attempt_id=attempt_id,
            question_id=question_id,
            question_version=question.version,
            answer_json=answer_json,
            time_spent_seconds=time_spent_seconds,
            answered_at=datetime.now(timezone.utc),
        )
        session.add(record)
    else:
        record.answer_json = answer_json
        record.time_spent_seconds = time_spent_seconds
        record.answered_at = datetime.now(timezone.utc)

    session.commit()
    session.refresh(record)
    return record


def get_attempt_payload(session: Session, attempt_id: int, *, user_id: int | None = None) -> dict | None:
    attempt = session.get(Attempt, attempt_id)
    if attempt is None or (user_id is not None and attempt.user_id != user_id):
        return None
    answers = list(
        session.scalars(
            select(AnswerRecord)
            .where(AnswerRecord.attempt_id == attempt_id)
            .order_by(AnswerRecord.id)
        ).all()
    )
    return {
        "id": attempt.id,
        "user_id": attempt.user_id,
        "subject_id": attempt.subject_id,
        "paper_id": attempt.paper_id,
        "mode": attempt.mode,
        "status": attempt.status,
        "started_at": attempt.started_at,
        "submitted_at": attempt.submitted_at,
        "score": attempt.score,
        "max_score": attempt.max_score,
        "answers": answers,
    }


def submit_attempt(session: Session, attempt_id: int, *, user_id: int | None = None) -> dict | None:
    from app.services.grading import grade_answer
    from app.services.learning_service import update_wrong_question
    from app.services.review_service import ensure_pending_review

    attempt = session.get(Attempt, attempt_id)
    if attempt is None or (user_id is not None and attempt.user_id != user_id):
        return None
    if attempt.status in {"submitted", "graded"}:
        return get_attempt_payload(session, attempt_id, user_id=user_id)

    answers = list(
        session.scalars(
            select(AnswerRecord).where(AnswerRecord.attempt_id == attempt_id).order_by(AnswerRecord.id)
        ).all()
    )
    total = 0.0
    max_score = 0.0
    has_manual = False
    for record in answers:
        question = session.get(Question, record.question_id)
        if question is None:
            continue
        max_score += float(question.score)
        result = grade_answer(question, record.answer_json)
        record.is_correct = result.is_correct
        record.auto_score = result.score
        if result.requires_manual:
            record.grading_status = "pending_manual"
            record.final_score = None
            ensure_pending_review(session, answer_id=record.id)
            has_manual = True
        else:
            record.grading_status = "auto"
            record.final_score = result.score
            total += float(result.score or 0)
            update_wrong_question(
                session,
                user_id=attempt.user_id,
                question_id=record.question_id,
                is_correct=bool(result.is_correct),
                attempt_mode=attempt.mode,
            )

    attempt.score = total
    attempt.max_score = max_score
    attempt.submitted_at = datetime.now(timezone.utc)
    attempt.status = "submitted" if has_manual else "graded"
    session.commit()
    return get_attempt_payload(session, attempt_id, user_id=user_id)
