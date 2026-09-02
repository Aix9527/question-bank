from __future__ import annotations

import json
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_review import AIReviewSuggestion
from app.models.attempt import AnswerRecord
from app.models.question_bank import Question
from app.services.review_service import ensure_pending_review


class AIGradingError(RuntimeError):
    pass


class AIGradingNotFound(AIGradingError):
    pass


def _html_text(value: str | None) -> str:
    if not value:
        return ''
    import html
    import re
    return html.unescape(re.sub(r'<[^>]+>', ' ', value)).strip()


def _standard_reference(question: Question) -> str:
    standard = question.standard_answer_json
    parts: list[str] = []
    if isinstance(standard, dict):
        for key in ('reference_html', 'value', 'answer'):
            value = standard.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(_html_text(value))
    if question.explanation_html:
        parts.append(_html_text(question.explanation_html))
    return '\n'.join(dict.fromkeys(part for part in parts if part))


def _learner_answer(answer: AnswerRecord) -> str:
    payload = answer.answer_json
    if isinstance(payload, dict):
        value = payload.get('value', payload.get('answer'))
        if value is None:
            return json.dumps(payload, ensure_ascii=False)
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)
    if payload is None:
        return ''
    return str(payload)


def build_grading_payload(question: Question, answer: AnswerRecord) -> dict[str, Any]:
    return {
        'question': _html_text(question.stem_html),
        'material': _html_text(question.material_html),
        'reference': _standard_reference(question),
        'learner_answer': _learner_answer(answer),
        'max_score': float(question.score),
        'knowledge_points': question.knowledge_points or [],
        'question_type': question.type,
    }


def _validate_result(result: Any, max_score: float) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise AIGradingError('AI provider returned a non-object result')
    try:
        score = float(result['suggested_score'])
    except (KeyError, TypeError, ValueError) as exc:
        raise AIGradingError('AI provider omitted a valid suggested_score') from exc
    if score < 0 or score > max_score:
        raise AIGradingError(f'AI suggested_score {score} is outside 0..{max_score}')
    confidence = str(result.get('confidence') or 'medium')
    if confidence not in {'low', 'medium', 'high'}:
        raise AIGradingError('AI confidence must be low, medium, or high')
    comment = str(result.get('comment') or '').strip()
    if not comment:
        raise AIGradingError('AI provider omitted comment')
    strengths = result.get('strengths') or []
    improvements = result.get('improvements') or []
    rubric = result.get('rubric') or []
    if not isinstance(strengths, list) or not isinstance(improvements, list) or not isinstance(rubric, list):
        raise AIGradingError('AI provider returned invalid list fields')
    return {
        'suggested_score': score,
        'confidence': confidence,
        'comment': comment,
        'strengths': [str(item) for item in strengths],
        'improvements': [str(item) for item in improvements],
        'rubric': rubric,
    }


def save_ai_suggestion(
    session: Session,
    *,
    answer_id: int,
    grader,
    provider: str = 'openai',
    model: str | None = None,
) -> AIReviewSuggestion:
    answer = session.get(AnswerRecord, answer_id)
    if answer is None:
        raise AIGradingNotFound('answer not found')
    question = session.get(Question, answer.question_id)
    if question is None:
        raise AIGradingNotFound('question not found')
    if question.answer_mode != 'manual':
        raise AIGradingError('AI suggestion is only available for manual-review questions')

    payload = build_grading_payload(question, answer)
    raw = grader.suggest(payload)
    result = _validate_result(raw, float(question.score))

    row = session.scalar(select(AIReviewSuggestion).where(AIReviewSuggestion.answer_id == answer_id))
    if row is None:
        row = AIReviewSuggestion(answer_id=answer_id, provider=provider, model=model, version=1, suggested_score=result['suggested_score'], confidence=result['confidence'], comment=result['comment'], strengths_json=result['strengths'], improvements_json=result['improvements'], rubric_json=result['rubric'], raw_json=raw)
        session.add(row)
    else:
        row.provider = provider
        row.model = model
        row.version += 1
        row.suggested_score = result['suggested_score']
        row.confidence = result['confidence']
        row.comment = result['comment']
        row.strengths_json = result['strengths']
        row.improvements_json = result['improvements']
        row.rubric_json = result['rubric']
        row.raw_json = raw

    review = ensure_pending_review(session, answer_id=answer_id)
    review.suggested_score = result['suggested_score']
    session.commit()
    session.refresh(row)
    return row


def suggestion_payload(row: AIReviewSuggestion) -> dict[str, Any]:
    return {
        'id': row.id,
        'answer_id': row.answer_id,
        'provider': row.provider,
        'model': row.model,
        'version': row.version,
        'suggested_score': row.suggested_score,
        'confidence': row.confidence,
        'comment': row.comment,
        'strengths': row.strengths_json or [],
        'improvements': row.improvements_json or [],
        'rubric': row.rubric_json or [],
        'created_at': row.created_at,
        'updated_at': row.updated_at,
    }


class OpenAIResponsesGrader:
    def __init__(self, *, api_key: str, model: str, base_url: str = 'https://api.openai.com/v1', client: httpx.Client | None = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.client = client or httpx.Client(timeout=60.0)

    def suggest(self, payload: dict[str, Any]) -> dict[str, Any]:
        max_score = float(payload['max_score'])
        schema = {
            'type': 'object',
            'properties': {
                'suggested_score': {'type': 'number', 'minimum': 0, 'maximum': max_score},
                'confidence': {'type': 'string', 'enum': ['low', 'medium', 'high']},
                'comment': {'type': 'string'},
                'strengths': {'type': 'array', 'items': {'type': 'string'}},
                'improvements': {'type': 'array', 'items': {'type': 'string'}},
                'rubric': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'criterion': {'type': 'string'},
                            'score': {'type': 'number'},
                            'max_score': {'type': 'number'},
                            'comment': {'type': 'string'},
                        },
                        'required': ['criterion', 'score', 'max_score', 'comment'],
                        'additionalProperties': False,
                    },
                },
            },
            'required': ['suggested_score', 'confidence', 'comment', 'strengths', 'improvements', 'rubric'],
            'additionalProperties': False,
        }
        prompt = (
            '你是成人高考复习题库的辅助阅卷员。只做建议，不决定最终成绩。\n'
            f"题型：{payload['question_type']}\n满分：{max_score}\n知识点：{', '.join(payload.get('knowledge_points') or [])}\n"
            f"题目：{payload['question']}\n材料：{payload.get('material') or ''}\n参考答案/评分说明：{payload.get('reference') or ''}\n"
            f"学生答案：{payload.get('learner_answer') or ''}\n"
            '请依据题目、参考答案和满分给出建议分、简明评语、优点、改进点和可解释的评分项。不要把建议分当作最终分。'
        )
        body = {
            'model': self.model,
            'store': False,
            'input': [
                {'role': 'developer', 'content': '输出必须严格遵循提供的 JSON Schema；不要输出额外文本。'},
                {'role': 'user', 'content': prompt},
            ],
            'text': {
                'format': {
                    'type': 'json_schema',
                    'name': 'question_bank_ai_review',
                    'strict': True,
                    'schema': schema,
                }
            },
        }
        response = self.client.post(
            f'{self.base_url}/responses',
            headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
            json=body,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AIGradingError(f'AI provider HTTP error: {response.status_code}') from exc
        data = response.json()
        text = data.get('output_text')
        if not isinstance(text, str):
            text = None
            for item in data.get('output') or []:
                if not isinstance(item, dict):
                    continue
                for content in item.get('content') or []:
                    if isinstance(content, dict) and content.get('type') == 'output_text' and isinstance(content.get('text'), str):
                        text = content['text']
                        break
                if text:
                    break
        if not text:
            raise AIGradingError('AI provider returned no output_text')
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIGradingError('AI provider returned invalid JSON') from exc


def build_ai_grader(settings):
    if settings.ai_provider == 'disabled' or not settings.openai_api_key:
        return None
    if settings.ai_provider != 'openai':
        raise ValueError(f'unsupported AI provider: {settings.ai_provider}')
    return OpenAIResponsesGrader(
        api_key=settings.openai_api_key,
        model=settings.ai_model,
        base_url=settings.openai_base_url,
    )
