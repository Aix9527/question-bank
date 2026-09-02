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


def test_bare_string_answer_payload_is_rejected_with_400(client):
    subject_id, question_id = _seed_question(client)
    attempt_id = client.post('/api/attempts', json={"subject_id": subject_id, "mode": "practice"}).json()['id']

    response = client.patch(
        f'/api/attempts/{attempt_id}/answers/{question_id}',
        json={"answer_json": "B", "time_spent_seconds": 2},
    )

    assert response.status_code == 400
    assert response.json()['detail'] == 'answer_json must be an object or null'
    restored = client.get(f'/api/attempts/{attempt_id}').json()
    assert restored['answers'] == []
