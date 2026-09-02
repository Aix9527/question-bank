"""为语文、数学、英语各创建一份 v0.2 本地演示卷。重复运行不会重复插入。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from sqlalchemy import select  # noqa: E402

from app.db import Base, build_engine, build_session_factory  # noqa: E402
from app.models import ai_review, attempt, core, learning, question_bank, review, user  # noqa: F401,E402
from app.models.core import Subject  # noqa: E402
from app.models.question_bank import Paper, PaperQuestion, PaperSection, Question, QuestionOption  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.services.bootstrap import seed_subjects, seed_users  # noqa: E402

DEMO_SOURCE_PREFIX = "demo://v0.2/"

DEMO = {
    "chinese": {
        "title": "语文 v0.2 演示卷",
        "questions": [
            ("single_choice", "下列词语中没有错别字的一项是？", "exact", {"value": "B"}, 5, ["字词基础"], [("A", "迫不急待"), ("B", "再接再厉"), ("C", "一愁莫展")]),
            ("fill_blank", "填写成语：学而不思则____。", "normalized_text", {"value": "罔"}, 5, ["语言积累"], []),
            ("essay", "请以“坚持”为主题写一段不少于 100 字的短文。", "manual", {"rubric": ["立意", "结构", "语言"]}, 20, ["作文"], []),
        ],
    },
    "math": {
        "title": "数学（文）v0.2 演示卷",
        "questions": [
            ("single_choice", "2 + 3 = ?", "exact", {"value": "C"}, 5, ["基础运算"], [("A", "3"), ("B", "4"), ("C", "5"), ("D", "6")]),
            ("fill_blank", "若 x + 2 = 5，则 x = ____。", "numeric_exact", {"value": 3}, 5, ["一元一次方程"], []),
            ("subjective", "写出方程 2x + 1 = 7 的解题过程。", "manual", {"rubric": ["列式", "过程", "结果"]}, 10, ["方程"], []),
        ],
    },
    "english": {
        "title": "英语 v0.2 演示卷",
        "questions": [
            ("single_choice", "Choose the correct answer: I ___ a student.", "exact", {"value": "A"}, 5, ["be 动词"], [("A", "am"), ("B", "is"), ("C", "are")]),
            ("fill_blank", "Translate into Chinese: hello", "multiple_acceptable", {"values": ["你好", "您好"]}, 5, ["词汇"], []),
            ("essay", "Write 50-80 words about your study plan.", "manual", {"rubric": ["grammar", "vocabulary", "structure"]}, 15, ["写作"], []),
        ],
    },
}


def main() -> None:
    engine = build_engine()
    Base.metadata.create_all(engine)
    Session = build_session_factory(engine)
    with Session() as session:
        seed_subjects(session)
        settings = get_settings()
        seed_users(session, admin_username=settings.bootstrap_admin_username, admin_password=settings.bootstrap_admin_password)
        for code, spec in DEMO.items():
            source = f"{DEMO_SOURCE_PREFIX}{code}"
            if session.scalar(select(Paper).where(Paper.source_file == source)) is not None:
                print(f"[skip] {spec['title']} 已存在")
                continue
            subject = session.scalar(select(Subject).where(Subject.code == code))
            paper = Paper(subject_id=subject.id, title=spec["title"], source_file=source, paper_type="mock", status="published", version=1)
            session.add(paper)
            session.flush()
            section = PaperSection(paper_id=paper.id, title="演示题", order_index=1, instruction="包含客观题、填空题和主观题", score_total=sum(q[4] for q in spec["questions"]))
            session.add(section)
            session.flush()
            for order, (qtype, stem, mode, standard, score, points, options) in enumerate(spec["questions"], start=1):
                question = Question(subject_id=subject.id, type=qtype, stem_html=stem, answer_mode=mode, standard_answer_json=standard, score=score, knowledge_points=points, source=source, status="published", version=1)
                session.add(question)
                session.flush()
                for option_order, (label, content) in enumerate(options, start=1):
                    session.add(QuestionOption(question_id=question.id, label=label, content_html=content, order_index=option_order))
                session.add(PaperQuestion(paper_id=paper.id, question_id=question.id, section_id=section.id, order_index=order, score_override=score))
            paper.total_score = section.score_total
            session.commit()
            print(f"[created] {spec['title']}")
    engine.dispose()


if __name__ == "__main__":
    main()
