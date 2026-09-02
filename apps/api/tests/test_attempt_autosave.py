from sqlalchemy import select


def _seed_question(client):
    from app.models.core import Subject
    from app.models.question_bank import Question

    with client.app.state.session_factory() as session:
        math = session.scalar(select(Subject).where(Subject.code == "math"))
        q = Question(
            subject_id=math.id,
            type="single_choice",
            stem_html="1+1=?",
            answer_mode="exact",
            standard_answer_json={"value": "B"},
            score=5,
            version=1,
            status="published",
        )
        session.add(q)
        session.commit()
        return math.id, q.id


def test_attempt_answer_is_autosaved_and_restored(client):
    subject_id, question_id = _seed_question(client)
    created = client.post('/api/attempts', json={"subject_id": subject_id, "mode": "practice"})
    assert created.status_code == 201
    attempt_id = created.json()['id']

    saved = client.patch(
        f'/api/attempts/{attempt_id}/answers/{question_id}',
        json={"answer_json": {"value": "B"}, "time_spent_seconds": 18},
    )
    assert saved.status_code == 200

    restored = client.get(f'/api/attempts/{attempt_id}')
    assert restored.status_code == 200
    body = restored.json()
    assert body['status'] == 'in_progress'
    assert len(body['answers']) == 1
    assert body['answers'][0]['question_id'] == question_id
    assert body['answers'][0]['answer_json'] == {"value": "B"}
    assert body['answers'][0]['time_spent_seconds'] == 18


def test_autosave_upserts_instead_of_duplicating_answer(client):
    subject_id, question_id = _seed_question(client)
    attempt_id = client.post('/api/attempts', json={"subject_id": subject_id, "mode": "practice"}).json()['id']

    client.patch(f'/api/attempts/{attempt_id}/answers/{question_id}', json={"answer_json": {"value": "A"}, "time_spent_seconds": 2})
    client.patch(f'/api/attempts/{attempt_id}/answers/{question_id}', json={"answer_json": {"value": "B"}, "time_spent_seconds": 7})

    body = client.get(f'/api/attempts/{attempt_id}').json()
    assert len(body['answers']) == 1
    assert body['answers'][0]['answer_json'] == {"value": "B"}
    assert body['answers'][0]['time_spent_seconds'] == 7
