from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_review import AIReviewSuggestion
from app.models.attempt import AnswerRecord, Attempt
from app.models.question_bank import Question
from app.models.review import ManualReview


def ensure_pending_review(session: Session, *, answer_id: int) -> ManualReview:
    review = session.scalar(select(ManualReview).where(ManualReview.answer_id == answer_id))
    if review is None:
        review = ManualReview(answer_id=answer_id, status="pending")
        session.add(review)
    return review


def list_pending_reviews(session: Session) -> list[dict]:
    rows = list(
        session.scalars(
            select(ManualReview)
            .where(ManualReview.status == "pending")
            .order_by(ManualReview.created_at, ManualReview.id)
        ).all()
    )
    payload: list[dict] = []
    for review in rows:
        answer = session.get(AnswerRecord, review.answer_id)
        if answer is None:
            continue
        question = session.get(Question, answer.question_id)
        if question is None:
            continue
        payload.append(_review_payload(review, answer, question, session))
    return payload


def _review_payload(review: ManualReview, answer: AnswerRecord, question: Question, session: Session | None = None) -> dict:
    ai = session.scalar(select(AIReviewSuggestion).where(AIReviewSuggestion.answer_id == answer.id)) if session is not None else None
    return {
        "id": review.id,
        "answer_id": answer.id,
        "attempt_id": answer.attempt_id,
        "question_id": question.id,
        "status": review.status,
        "suggested_score": review.suggested_score,
        "final_score": review.final_score,
        "comment": review.comment,
        "rubric_json": review.rubric_json,
        "reviewer_user_id": review.reviewer_user_id,
        "created_at": review.created_at,
        "reviewed_at": review.reviewed_at,
        "max_score": float(question.score),
        "answer_json": answer.answer_json,
        "ai_suggestion": ({
            "id": ai.id, "answer_id": ai.answer_id, "provider": ai.provider, "model": ai.model,
            "version": ai.version, "suggested_score": ai.suggested_score, "confidence": ai.confidence,
            "comment": ai.comment, "strengths": ai.strengths_json or [], "improvements": ai.improvements_json or [],
            "rubric": ai.rubric_json or [], "created_at": ai.created_at, "updated_at": ai.updated_at,
        } if ai is not None else None),
        "question": {
            "id": question.id,
            "type": question.type,
            "stem_html": question.stem_html,
            "material_html": question.material_html,
            "score": float(question.score),
            "knowledge_points": question.knowledge_points,
        },
    }


def recompute_attempt_score(session: Session, attempt_id: int) -> Attempt | None:
    attempt = session.get(Attempt, attempt_id)
    if attempt is None:
        return None
    answers = list(session.scalars(select(AnswerRecord).where(AnswerRecord.attempt_id == attempt_id)).all())
    attempt.score = sum(float(answer.final_score or 0.0) for answer in answers)
    pending_count = session.scalar(
        select(func.count(AnswerRecord.id)).where(
            AnswerRecord.attempt_id == attempt_id,
            AnswerRecord.grading_status == "pending_manual",
        )
    ) or 0
    attempt.status = "submitted" if pending_count else "graded"
    return attempt


def submit_manual_review(
    session: Session,
    *,
    answer_id: int,
    suggested_score: float | None,
    final_score: float,
    comment: str | None,
    rubric_json,
    reviewer_user_id: int = 1,
) -> tuple[dict | None, str | None]:
    answer = session.get(AnswerRecord, answer_id)
    if answer is None:
        return None, "answer not found"
    question = session.get(Question, answer.question_id)
    if question is None:
        return None, "question not found"
    max_score = float(question.score)
    if final_score < 0 or final_score > max_score:
        return None, f"final_score must be between 0 and {max_score}"
    if suggested_score is not None and (suggested_score < 0 or suggested_score > max_score):
        return None, f"suggested_score must be between 0 and {max_score}"

    review = ensure_pending_review(session, answer_id=answer_id)
    review.status = "reviewed"
    review.suggested_score = suggested_score
    review.final_score = final_score
    review.comment = comment
    review.rubric_json = rubric_json
    review.reviewer_user_id = reviewer_user_id
    review.reviewed_at = datetime.now(timezone.utc)

    answer.final_score = final_score
    answer.grading_status = "reviewed"
    recompute_attempt_score(session, answer.attempt_id)
    session.commit()
    session.refresh(review)
    session.refresh(answer)
    return _review_payload(review, answer, question, session), None
