"""清理测试作答与派生记录；默认仅 user_id=1，收藏保留。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from sqlalchemy import delete, select  # noqa: E402

from app.db import Base, build_engine, build_session_factory  # noqa: E402
from app.models import ai_review, attempt, core, learning, question_bank, review, user  # noqa: F401,E402
from app.models.ai_review import AIReviewSuggestion  # noqa: E402
from app.models.attempt import AnswerRecord, Attempt  # noqa: E402
from app.models.learning import WrongQuestion  # noqa: E402
from app.models.review import ManualReview  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="清理测试作答/批改/错题，收藏与题库保留。")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--user-id", type=int, default=1, help="仅清理指定用户，默认 1")
    group.add_argument("--all-users", action="store_true", help="清理所有用户的作答/批改/错题")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    engine = build_engine()
    Base.metadata.create_all(engine)
    Session = build_session_factory(engine)
    with Session() as session:
        if args.all_users:
            ai_count = session.execute(delete(AIReviewSuggestion)).rowcount
            review_count = session.execute(delete(ManualReview)).rowcount
            answer_count = session.execute(delete(AnswerRecord)).rowcount
            attempt_count = session.execute(delete(Attempt)).rowcount
            wrong_count = session.execute(delete(WrongQuestion)).rowcount
            scope = "all users"
        else:
            user_id = args.user_id
            attempt_ids = select(Attempt.id).where(Attempt.user_id == user_id)
            answer_ids = select(AnswerRecord.id).where(AnswerRecord.attempt_id.in_(attempt_ids))
            ai_count = session.execute(delete(AIReviewSuggestion).where(AIReviewSuggestion.answer_id.in_(answer_ids))).rowcount
            review_count = session.execute(delete(ManualReview).where(ManualReview.answer_id.in_(answer_ids))).rowcount
            answer_count = session.execute(delete(AnswerRecord).where(AnswerRecord.attempt_id.in_(attempt_ids))).rowcount
            attempt_count = session.execute(delete(Attempt).where(Attempt.user_id == user_id)).rowcount
            wrong_count = session.execute(delete(WrongQuestion).where(WrongQuestion.user_id == user_id)).rowcount
            scope = f"user_id={user_id}"
        session.commit()
    engine.dispose()
    print(
        f"已清理 {scope}：attempts={attempt_count}, answers={answer_count}, reviews={review_count}, "
        f"ai_suggestions={ai_count}, wrong_questions={wrong_count}"
    )
    print("收藏 favorites、账号 users 与题库数据未删除。")


if __name__ == "__main__":
    main()
