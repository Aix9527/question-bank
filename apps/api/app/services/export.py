from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.models.ai_review import AIReviewSuggestion
from app.models.attempt import AnswerRecord, Attempt
from app.models.core import Subject
from app.models.import_job import ImportJob
from app.models.learning import Favorite, WrongQuestion
from app.models.question_bank import Paper, PaperQuestion, PaperSection, Question, QuestionOption
from app.models.review import ManualReview
from app.models.user import User


QUESTION_BANK_TABLES = {
    'subjects': Subject,
    'papers': Paper,
    'paper_sections': PaperSection,
    'questions': Question,
    'question_options': QuestionOption,
    'paper_questions': PaperQuestion,
    'import_jobs': ImportJob,
}

LEARNING_TABLES = {
    'attempts': Attempt,
    'answer_records': AnswerRecord,
    'wrong_questions': WrongQuestion,
    'favorites': Favorite,
    'manual_reviews': ManualReview,
    'ai_review_suggestions': AIReviewSuggestion,
}


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _model_row(instance: Any) -> dict[str, Any]:
    mapper = sa_inspect(instance.__class__)
    return {column.key: _json_value(getattr(instance, column.key)) for column in mapper.columns}


def _table_rows(session: Session, model: type) -> list[dict[str, Any]]:
    return [_model_row(item) for item in session.scalars(select(model).order_by(model.id)).all()]


def _safe_user_rows(session: Session) -> list[dict[str, Any]]:
    rows = []
    for user in session.scalars(select(User).order_by(User.id)).all():
        rows.append({
            'id': user.id,
            'username': user.username,
            'display_name': user.display_name,
            'role': user.role,
            'enabled': user.enabled,
            'created_at': _json_value(user.created_at),
            'updated_at': _json_value(user.updated_at),
        })
    return rows


def build_export(session: Session) -> dict[str, Any]:
    return {
        'schema_version': 1,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'question_bank': {name: _table_rows(session, model) for name, model in QUESTION_BANK_TABLES.items()},
        'learning': {name: _table_rows(session, model) for name, model in LEARNING_TABLES.items()},
        'accounts': {'users': _safe_user_rows(session)},
    }


def _csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO(newline='')
    fieldnames = list(rows[0].keys()) if rows else ['id']
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({
            key: json.dumps(value, ensure_ascii=False, separators=(',', ':')) if isinstance(value, (dict, list)) else value
            for key, value in row.items()
        })
    return ('\ufeff' + buffer.getvalue()).encode('utf-8')


def build_csv_zip(export: dict[str, Any]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode='w', compression=zipfile.ZIP_DEFLATED) as archive:
        for group_name in ('question_bank', 'learning', 'accounts'):
            for table_name, rows in export[group_name].items():
                archive.writestr(f'{table_name}.csv', _csv_bytes(rows))
        archive.writestr(
            'manifest.json',
            json.dumps(
                {
                    'schema_version': export['schema_version'],
                    'generated_at': export['generated_at'],
                    'tables': {
                        group: {name: len(rows) for name, rows in export[group].items()}
                        for group in ('question_bank', 'learning', 'accounts')
                    },
                },
                ensure_ascii=False,
                indent=2,
            ).encode('utf-8'),
        )
    return output.getvalue()
