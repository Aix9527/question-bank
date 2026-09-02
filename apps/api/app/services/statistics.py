from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attempt import AnswerRecord, Attempt
from app.models.core import Subject
from app.models.learning import WrongQuestion
from app.models.question_bank import Paper, Question


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _ratio(numerator: float, denominator: float) -> float | None:
    if not denominator:
        return None
    return round(numerator / denominator, 4)


def get_history(session: Session, *, user_id: int = 1) -> list[dict]:
    attempts = list(
        session.scalars(
            select(Attempt)
            .where(Attempt.user_id == user_id, Attempt.submitted_at.is_not(None))
            .order_by(Attempt.submitted_at.desc(), Attempt.id.desc())
        ).all()
    )
    payload: list[dict] = []
    for attempt in attempts:
        subject = session.get(Subject, attempt.subject_id)
        paper = session.get(Paper, attempt.paper_id) if attempt.paper_id is not None else None
        pending_manual = sum(
            1
            for record in session.scalars(select(AnswerRecord).where(AnswerRecord.attempt_id == attempt.id)).all()
            if record.grading_status == "pending_manual"
        )
        payload.append(
            {
                "id": attempt.id,
                "subject_id": attempt.subject_id,
                "subject_code": subject.code if subject else None,
                "subject_name": subject.name if subject else None,
                "paper_id": attempt.paper_id,
                "paper_title": paper.title if paper else None,
                "mode": attempt.mode,
                "status": attempt.status,
                "started_at": attempt.started_at,
                "submitted_at": attempt.submitted_at,
                "score": attempt.score,
                "max_score": attempt.max_score,
                "score_rate": _ratio(float(attempt.score or 0.0), float(attempt.max_score or 0.0)),
                "pending_manual_count": pending_manual,
            }
        )
    return payload


def get_statistics(session: Session, *, user_id: int = 1) -> dict:
    now = datetime.now(timezone.utc)
    attempts = list(
        session.scalars(
            select(Attempt)
            .where(Attempt.user_id == user_id, Attempt.submitted_at.is_not(None))
            .order_by(Attempt.submitted_at, Attempt.id)
        ).all()
    )
    answers: list[tuple[AnswerRecord, Attempt, Question]] = []
    for attempt in attempts:
        for answer in session.scalars(select(AnswerRecord).where(AnswerRecord.attempt_id == attempt.id)).all():
            question = session.get(Question, answer.question_id)
            if question is not None:
                answers.append((answer, attempt, question))

    objective = [(answer, attempt, question) for answer, attempt, question in answers if answer.is_correct is not None]
    correct_count = sum(1 for answer, _, _ in objective if answer.is_correct is True)
    wrong_rows = list(session.scalars(select(WrongQuestion).where(WrongQuestion.user_id == user_id)).all())

    subject_stats: dict[int, dict] = {}
    subjects = list(session.scalars(select(Subject).where(Subject.enabled.is_(True)).order_by(Subject.id)).all())
    for subject in subjects:
        subject_attempts = [attempt for attempt in attempts if attempt.subject_id == subject.id]
        subject_answers = [(answer, attempt, question) for answer, attempt, question in objective if question.subject_id == subject.id]
        subject_correct = sum(1 for answer, _, _ in subject_answers if answer.is_correct is True)
        subject_wrong = [row for row in wrong_rows if (session.get(Question, row.question_id) or type("X", (), {"subject_id": None})()).subject_id == subject.id]
        score_sum = sum(float(attempt.score or 0.0) for attempt in subject_attempts)
        max_sum = sum(float(attempt.max_score or 0.0) for attempt in subject_attempts)
        subject_stats[subject.id] = {
            "subject_id": subject.id,
            "code": subject.code,
            "name": subject.name,
            "attempts": len(subject_attempts),
            "objective_answers": len(subject_answers),
            "correct_answers": subject_correct,
            "accuracy": _ratio(subject_correct, len(subject_answers)),
            "score_rate": _ratio(score_sum, max_sum),
            "wrong_questions": len(subject_wrong),
            "mastered_wrong_questions": sum(1 for row in subject_wrong if row.state == "mastered"),
        }

    by_type: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_knowledge: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for answer, _, question in objective:
        by_type[question.type][0] += 1
        by_type[question.type][1] += int(answer.is_correct is True)
        for point in question.knowledge_points or []:
            by_knowledge[point][0] += 1
            by_knowledge[point][1] += int(answer.is_correct is True)

    exam_trend = []
    for attempt in attempts:
        subject = session.get(Subject, attempt.subject_id)
        exam_trend.append(
            {
                "attempt_id": attempt.id,
                "subject_code": subject.code if subject else None,
                "paper_id": attempt.paper_id,
                "submitted_at": attempt.submitted_at,
                "score": attempt.score,
                "max_score": attempt.max_score,
                "score_rate": _ratio(float(attempt.score or 0.0), float(attempt.max_score or 0.0)),
            }
        )

    return {
        "generated_at": now,
        "totals": {
            "attempts": len(attempts),
            "answered_questions": len(answers),
            "objective_answers": len(objective),
            "correct_answers": correct_count,
            "accuracy": _ratio(correct_count, len(objective)),
            "wrong_questions": len(wrong_rows),
            "mastered_wrong_questions": sum(1 for row in wrong_rows if row.state == "mastered"),
            "repeat_wrong_questions": sum(1 for row in wrong_rows if row.wrong_count >= 2),
        },
        "activity": {
            "last_7_days_answers": sum(1 for answer, _, _ in answers if _as_utc(answer.answered_at) >= now - timedelta(days=7)),
            "last_30_days_answers": sum(1 for answer, _, _ in answers if _as_utc(answer.answered_at) >= now - timedelta(days=30)),
        },
        "subjects": list(subject_stats.values()),
        "exam_trend": exam_trend,
        "question_type_accuracy": [
            {"question_type": key, "answered": value[0], "correct": value[1], "accuracy": _ratio(value[1], value[0])}
            for key, value in sorted(by_type.items())
        ],
        "knowledge_point_accuracy": [
            {"knowledge_point": key, "answered": value[0], "correct": value[1], "accuracy": _ratio(value[1], value[0])}
            for key, value in sorted(by_knowledge.items())
        ],
    }
