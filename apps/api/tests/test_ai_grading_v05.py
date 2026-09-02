from __future__ import annotations

import json

import httpx
from sqlalchemy import select


def _seed_subjective_pending(client):
    from app.models.core import Subject
    from app.models.question_bank import Question

    with client.app.state.session_factory() as session:
        chinese = session.scalar(select(Subject).where(Subject.code == 'chinese'))
        q = Question(
            subject_id=chinese.id,
            type='essay',
            stem_html='围绕“坚持”写一篇文章。',
            answer_mode='manual',
            standard_answer_json={'reference_html': '立意明确，结构完整，语言通顺。'},
            explanation_html='评分重点：立意、结构、语言。',
            score=20,
            knowledge_points=['语文/写作/作文'],
            version=1,
            status='published',
        )
        session.add(q)
        session.commit()
        subject_id, question_id = chinese.id, q.id

    attempt_id = client.post('/api/attempts', json={'subject_id': subject_id, 'mode': 'practice'}).json()['id']
    saved = client.patch(
        f'/api/attempts/{attempt_id}/answers/{question_id}',
        json={'answer_json': {'value': '坚持能够让人在困难中不断前进。'}, 'time_spent_seconds': 120},
    ).json()
    client.post(f'/api/attempts/{attempt_id}/submit')
    return attempt_id, saved['id']


class FakeGrader:
    def __init__(self, score=15):
        self.score = score
        self.calls = 0

    def suggest(self, payload):
        self.calls += 1
        assert payload['max_score'] == 20.0
        assert '坚持能够让人' in payload['learner_answer']
        return {
            'suggested_score': self.score,
            'confidence': 'high',
            'comment': '立意明确，结构基本完整。',
            'strengths': ['中心明确'],
            'improvements': ['增加论据'],
            'rubric': [
                {'criterion': '立意', 'score': 6, 'max_score': 7, 'comment': '明确'},
                {'criterion': '结构', 'score': 5, 'max_score': 7, 'comment': '基本完整'},
                {'criterion': '语言', 'score': 4, 'max_score': 6, 'comment': '通顺'},
            ],
        }


def test_ai_suggestion_is_advisory_persisted_and_refreshable(client):
    attempt_id, answer_id = _seed_subjective_pending(client)
    grader = FakeGrader(15)
    client.app.state.ai_grader = grader

    first = client.post(f'/api/admin/reviews/{answer_id}/ai-suggest')
    assert first.status_code == 200
    body = first.json()
    assert body['answer_id'] == answer_id
    assert body['suggested_score'] == 15
    assert body['version'] == 1
    assert body['confidence'] == 'high'

    attempt = client.get(f'/api/attempts/{attempt_id}').json()
    assert attempt['status'] == 'submitted'
    assert attempt['answers'][0]['final_score'] is None

    pending = client.get('/api/admin/reviews/pending').json()[0]
    assert pending['suggested_score'] == 15
    assert pending['final_score'] is None
    assert pending['ai_suggestion']['suggested_score'] == 15
    assert pending['ai_suggestion']['comment'].startswith('立意明确')

    grader.score = 16
    second = client.post(f'/api/admin/reviews/{answer_id}/ai-suggest')
    assert second.status_code == 200
    assert second.json()['suggested_score'] == 16
    assert second.json()['version'] == 2
    assert grader.calls == 2


def test_ai_suggestion_rejects_out_of_range_score_and_disabled_provider(client):
    _, answer_id = _seed_subjective_pending(client)
    client.app.state.ai_grader = None
    assert client.post(f'/api/admin/reviews/{answer_id}/ai-suggest').status_code == 503

    client.app.state.ai_grader = FakeGrader(25)
    response = client.post(f'/api/admin/reviews/{answer_id}/ai-suggest')
    assert response.status_code == 502
    assert 'outside' in response.json()['detail']


def test_openai_responses_grader_uses_structured_output_and_parses_response():
    from app.services.ai_grading import OpenAIResponsesGrader

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured['authorization'] = request.headers['authorization']
        body = json.loads(request.content)
        captured['body'] = body
        result = {
            'suggested_score': 8,
            'confidence': 'medium',
            'comment': '要点基本覆盖。',
            'strengths': ['答到核心'],
            'improvements': ['表达更准确'],
            'rubric': [],
        }
        return httpx.Response(
            200,
            json={'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(result, ensure_ascii=False)}]}]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    grader = OpenAIResponsesGrader(api_key='sk-test', model='test-model', base_url='https://api.openai.com/v1', client=client)
    result = grader.suggest({
        'question': '简述作用。', 'material': '', 'reference': '参考答案', 'learner_answer': '学生答案',
        'max_score': 10.0, 'knowledge_points': ['语文/阅读/简答'], 'question_type': 'short_answer',
    })
    assert result['suggested_score'] == 8
    assert captured['authorization'] == 'Bearer sk-test'
    assert captured['body']['model'] == 'test-model'
    assert captured['body']['text']['format']['type'] == 'json_schema'
    assert captured['body']['text']['format']['strict'] is True
    assert captured['body']['text']['format']['schema']['properties']['suggested_score']['maximum'] == 10.0
