from sqlalchemy import select


def _seed_objective_question(client):
    from app.models.core import Subject
    from app.models.question_bank import Question, QuestionOption

    with client.app.state.session_factory() as session:
        math = session.scalar(select(Subject).where(Subject.code == "math"))
        q = Question(
            subject_id=math.id,
            type="single_choice",
            stem_html="2+2=?",
            answer_mode="exact",
            standard_answer_json={"value": "C"},
            explanation_html="2+2=4",
            score=5,
            knowledge_points=["基础运算"],
            version=1,
            status="published",
        )
        session.add(q)
        session.flush()
        session.add_all([
            QuestionOption(question_id=q.id, label="A", content_html="2", order_index=1),
            QuestionOption(question_id=q.id, label="C", content_html="4", order_index=2),
        ])
        session.commit()
        return math.id, q.id


def _submit_answer(client, subject_id, question_id, value, mode="practice"):
    attempt_id = client.post('/api/attempts', json={"subject_id": subject_id, "mode": mode}).json()['id']
    saved = client.patch(
        f'/api/attempts/{attempt_id}/answers/{question_id}',
        json={"answer_json": {"value": value}, "time_spent_seconds": 3},
    )
    assert saved.status_code == 200
    submitted = client.post(f'/api/attempts/{attempt_id}/submit')
    assert submitted.status_code == 200
    return attempt_id


def test_wrong_question_lifecycle_moves_to_mastered_after_two_correct_reviews(client):
    subject_id, question_id = _seed_objective_question(client)

    _submit_answer(client, subject_id, question_id, "A")
    first = client.get('/api/me/wrong-questions').json()
    assert len(first) == 1
    assert first[0]['question_id'] == question_id
    assert first[0]['state'] == 'pending'
    assert first[0]['wrong_count'] == 1
    assert first[0]['correct_review_count'] == 0
    assert first[0]['consecutive_correct_count'] == 0

    _submit_answer(client, subject_id, question_id, "C", mode="wrong_review")
    second = client.get('/api/me/wrong-questions').json()[0]
    assert second['state'] == 'learning'
    assert second['correct_review_count'] == 1
    assert second['consecutive_correct_count'] == 1

    _submit_answer(client, subject_id, question_id, "C", mode="wrong_review")
    mastered = client.get('/api/me/wrong-questions').json()[0]
    assert mastered['state'] == 'mastered'
    assert mastered['correct_review_count'] == 2
    assert mastered['consecutive_correct_count'] == 2

    _submit_answer(client, subject_id, question_id, "A", mode="wrong_review")
    relapsed = client.get('/api/me/wrong-questions').json()[0]
    assert relapsed['state'] == 'pending'
    assert relapsed['wrong_count'] == 2
    assert relapsed['consecutive_correct_count'] == 0


def test_review_attempt_endpoint_returns_pending_wrong_questions(client):
    subject_id, question_id = _seed_objective_question(client)
    _submit_answer(client, subject_id, question_id, "A")

    response = client.post('/api/me/wrong-questions/review-attempt', json={})

    assert response.status_code == 201
    body = response.json()
    assert body['attempt']['mode'] == 'wrong_review'
    assert body['question_ids'] == [question_id]


def test_favorite_is_idempotent_and_can_be_removed(client):
    _, question_id = _seed_objective_question(client)

    first = client.post(f'/api/questions/{question_id}/favorite')
    second = client.post(f'/api/questions/{question_id}/favorite')
    assert first.status_code == 201
    assert second.status_code == 200

    favorites = client.get('/api/me/favorites')
    assert favorites.status_code == 200
    assert [item['question_id'] for item in favorites.json()] == [question_id]
    assert favorites.json()[0]['question']['stem_html'] == '2+2=?'

    removed = client.delete(f'/api/questions/{question_id}/favorite')
    assert removed.status_code == 204
    assert client.get('/api/me/favorites').json() == []
