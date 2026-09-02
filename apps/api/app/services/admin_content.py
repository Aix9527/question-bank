from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import Subject
from app.models.question_bank import Paper, PaperQuestion, PaperSection, Question, QuestionOption


def _subject(session: Session, code: str) -> Subject | None:
    return session.scalar(select(Subject).where(Subject.code == code))


def question_payload(session: Session, question: Question) -> dict[str, Any]:
    subject = session.get(Subject, question.subject_id)
    options = sorted(question.options, key=lambda item: item.order_index)
    return {
        'id': question.id,
        'subject_id': question.subject_id,
        'subject_code': subject.code if subject else '',
        'type': question.type,
        'stem_html': question.stem_html,
        'material_html': question.material_html,
        'answer_mode': question.answer_mode,
        'standard_answer_json': question.standard_answer_json,
        'explanation_html': question.explanation_html,
        'score': float(question.score),
        'difficulty': question.difficulty,
        'knowledge_points': question.knowledge_points,
        'source': question.source,
        'status': question.status,
        'version': question.version,
        'options': [
            {
                'id': option.id,
                'label': option.label,
                'content_html': option.content_html,
                'order_index': option.order_index,
            }
            for option in options
        ],
    }


def list_questions(
    session: Session, *, subject_code: str | None = None, status: str | None = None,
    question_type: str | None = None, limit: int = 200,
) -> list[dict[str, Any]]:
    stmt = select(Question).order_by(Question.id.desc()).limit(limit)
    if subject_code:
        subject = _subject(session, subject_code)
        if subject is None:
            return []
        stmt = stmt.where(Question.subject_id == subject.id)
    if status:
        stmt = stmt.where(Question.status == status)
    if question_type:
        stmt = stmt.where(Question.type == question_type)
    return [question_payload(session, item) for item in session.scalars(stmt).all()]


def create_question(session: Session, data: dict[str, Any]) -> Question | None:
    subject = _subject(session, str(data.pop('subject_code')))
    if subject is None:
        return None
    options = data.pop('options', [])
    question = Question(subject_id=subject.id, **data)
    session.add(question)
    session.flush()
    for option in options:
        session.add(QuestionOption(question_id=question.id, **option))
    session.commit()
    session.refresh(question)
    return question


def update_question(session: Session, question: Question, data: dict[str, Any]) -> Question:
    options = data.pop('options', None)
    changed = bool(data) or options is not None
    for key, value in data.items():
        setattr(question, key, value)
    if options is not None:
        question.options.clear()
        session.flush()
        for option in options:
            question.options.append(QuestionOption(**option))
    if changed:
        question.version += 1
    session.add(question)
    session.commit()
    session.refresh(question)
    return question


def archive_question(session: Session, question: Question) -> Question:
    if question.status != 'archived':
        question.status = 'archived'
        question.version += 1
        session.add(question)
        session.commit()
        session.refresh(question)
    return question


def paper_payload(session: Session, paper: Paper) -> dict[str, Any]:
    subject = session.get(Subject, paper.subject_id)
    section_count = session.scalar(select(func.count(PaperSection.id)).where(PaperSection.paper_id == paper.id)) or 0
    question_count = session.scalar(select(func.count(PaperQuestion.id)).where(PaperQuestion.paper_id == paper.id)) or 0
    return {
        'id': paper.id,
        'subject_id': paper.subject_id,
        'subject_code': subject.code if subject else '',
        'title': paper.title,
        'source_file': paper.source_file,
        'paper_type': paper.paper_type,
        'total_score': paper.total_score,
        'time_limit_minutes': paper.time_limit_minutes,
        'status': paper.status,
        'version': paper.version,
        'section_count': int(section_count),
        'question_count': int(question_count),
    }


def list_papers(session: Session, *, subject_code: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    stmt = select(Paper).order_by(Paper.id.desc())
    if subject_code:
        subject = _subject(session, subject_code)
        if subject is None:
            return []
        stmt = stmt.where(Paper.subject_id == subject.id)
    if status:
        stmt = stmt.where(Paper.status == status)
    return [paper_payload(session, item) for item in session.scalars(stmt).all()]


def create_paper(session: Session, data: dict[str, Any]) -> Paper | None:
    subject = _subject(session, str(data.pop('subject_code')))
    if subject is None:
        return None
    paper = Paper(subject_id=subject.id, **data)
    session.add(paper)
    session.commit()
    session.refresh(paper)
    return paper


def update_paper(session: Session, paper: Paper, data: dict[str, Any]) -> Paper:
    if data:
        for key, value in data.items():
            setattr(paper, key, value)
        paper.version += 1
        session.add(paper)
        session.commit()
        session.refresh(paper)
    return paper


def archive_paper(session: Session, paper: Paper) -> Paper:
    if paper.status != 'archived':
        paper.status = 'archived'
        paper.version += 1
        session.add(paper)
        session.commit()
        session.refresh(paper)
    return paper
