"""清理学习数据；默认只清理 user_id=1，可显式选择其他用户或全部用户。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from sqlalchemy import delete, select  # noqa: E402

from app.db import Base, build_engine, build_session_factory  # noqa: E402
from app.models import ai_review, attempt, core, import_job, learning, question_bank, review, user  # noqa: F401,E402
from app.models.ai_review import AIReviewSuggestion  # noqa: E402
from app.models.attempt import AnswerRecord, Attempt  # noqa: E402
from app.models.learning import Favorite, WrongQuestion  # noqa: E402
from app.models.review import ManualReview  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="清理学习者作答/错题/收藏/批改数据，题库与账号保留。")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--user-id", type=int, default=1, help="仅清理指定用户，默认 1（兼容旧单机模式）")
    group.add_argument("--all-users", action="store_true", help="清理所有用户的学习数据（危险操作）")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    engine = build_engine()
    Base.metadata.create_all(engine)
    Session = build_session_factory(engine)
    with Session() as session:
        if args.all_users:
            ai_rows = session.execute(delete(AIReviewSuggestion)).rowcount
            reviews = session.execute(delete(ManualReview)).rowcount
            answers = session.execute(delete(AnswerRecord)).rowcount
            attempts = session.execute(delete(Attempt)).rowcount
            wrong = session.execute(delete(WrongQuestion)).rowcount
            favorites = session.execute(delete(Favorite)).rowcount
            scope = "all users"
        else:
            user_id = args.user_id
            attempt_ids = select(Attempt.id).where(Attempt.user_id == user_id)
            answer_ids = select(AnswerRecord.id).where(AnswerRecord.attempt_id.in_(attempt_ids))
            ai_rows = session.execute(delete(AIReviewSuggestion).where(AIReviewSuggestion.answer_id.in_(answer_ids))).rowcount
            reviews = session.execute(delete(ManualReview).where(ManualReview.answer_id.in_(answer_ids))).rowcount
            answers = session.execute(delete(AnswerRecord).where(AnswerRecord.attempt_id.in_(attempt_ids))).rowcount
            attempts = session.execute(delete(Attempt).where(Attempt.user_id == user_id)).rowcount
            wrong = session.execute(delete(WrongQuestion).where(WrongQuestion.user_id == user_id)).rowcount
            favorites = session.execute(delete(Favorite).where(Favorite.user_id == user_id)).rowcount
            scope = f"user_id={user_id}"
        session.commit()
    engine.dispose()
    print(
        f"已清理 {scope} 学习数据："
        f"attempts={attempts}, answers={answers}, reviews={reviews}, ai_suggestions={ai_rows}, "
        f"wrong_questions={wrong}, favorites={favorites}"
    )
    print("账号、题库、试卷和 DOCX 导入/发布记录均保留。")


if __name__ == "__main__":
    main()
