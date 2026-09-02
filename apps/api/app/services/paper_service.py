from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Subject
from app.models.question_bank import Paper, PaperQuestion, PaperSection, Question, QuestionOption


def list_published_papers(session: Session, subject_code: str) -> list[Paper]:
    stmt = (
        select(Paper)
        .join(Subject, Subject.id == Paper.subject_id)
        .where(Subject.code == subject_code, Paper.status == "published")
        .order_by(Paper.id)
    )
    return list(session.scalars(stmt).all())


def get_paper_detail(session: Session, paper_id: int) -> dict | None:
    paper = session.get(Paper, paper_id)
    if paper is None:
        return None

    sections = list(
        session.scalars(
            select(PaperSection)
            .where(PaperSection.paper_id == paper.id)
            .order_by(PaperSection.order_index, PaperSection.id)
        ).all()
    )

    section_payloads: list[dict] = []
    for section in sections:
        links = list(
            session.scalars(
                select(PaperQuestion)
                .where(PaperQuestion.paper_id == paper.id, PaperQuestion.section_id == section.id)
                .order_by(PaperQuestion.order_index, PaperQuestion.id)
            ).all()
        )
        questions: list[dict] = []
        for link in links:
            question = session.get(Question, link.question_id)
            if question is None:
                continue
            options = list(
                session.scalars(
                    select(QuestionOption)
                    .where(QuestionOption.question_id == question.id)
                    .order_by(QuestionOption.order_index, QuestionOption.id)
                ).all()
            )
            questions.append(
                {
                    "id": question.id,
                    "type": question.type,
                    "stem_html": question.stem_html,
                    "material_html": question.material_html,
                    "answer_mode": question.answer_mode,
                    "standard_answer_json": question.standard_answer_json,
                    "explanation_html": question.explanation_html,
                    "score": link.score_override if link.score_override is not None else question.score,
                    "difficulty": question.difficulty,
                    "knowledge_points": question.knowledge_points,
                    "version": question.version,
                    "options": options,
                }
            )
        section_payloads.append(
            {
                "id": section.id,
                "title": section.title,
                "order_index": section.order_index,
                "instruction": section.instruction,
                "score_total": section.score_total,
                "questions": questions,
            }
        )

    return {
        "id": paper.id,
        "subject_id": paper.subject_id,
        "title": paper.title,
        "paper_type": paper.paper_type,
        "total_score": paper.total_score,
        "time_limit_minutes": paper.time_limit_minutes,
        "status": paper.status,
        "version": paper.version,
        "sections": section_payloads,
    }
