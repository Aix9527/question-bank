from sqlalchemy import func, select


def _seed_attempt(client):
    from app.models.core import Subject
    from app.models.question_bank import Question

    with client.app.state.session_factory() as session:
        math = session.scalar(select(Subject).where(Subject.code == 'math'))
        q = Question(subject_id=math.id, type='single_choice', stem_html='1+1=?', answer_mode='exact', standard_answer_json={'value': 'B'}, score=5, version=1, status='published')
        session.add(q)
        session.commit()
        qid = q.id
        sid = math.id
    attempt_id = client.post('/api/attempts', json={'subject_id': sid, 'mode': 'practice'}).json()['id']
    client.patch(f'/api/attempts/{attempt_id}/answers/{qid}', json={'answer_json': {'value': 'B'}, 'time_spent_seconds': 2})
    return attempt_id


def test_submit_is_idempotent(client):
    from app.models.attempt import AnswerRecord

    attempt_id = _seed_attempt(client)
    first = client.post(f'/api/attempts/{attempt_id}/submit')
    second = client.post(f'/api/attempts/{attempt_id}/submit')

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()['status'] == 'graded'
    assert first.json()['score'] == 5
    assert second.json()['score'] == 5

    with client.app.state.session_factory() as session:
        count = session.scalar(select(func.count(AnswerRecord.id)).where(AnswerRecord.attempt_id == attempt_id))
        assert count == 1
