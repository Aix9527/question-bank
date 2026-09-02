from sqlalchemy import select


def _seed_subjective_question(client):
    from app.models.core import Subject
    from app.models.question_bank import Question

    with client.app.state.session_factory() as session:
        chinese = session.scalar(select(Subject).where(Subject.code == "chinese"))
        q = Question(
            subject_id=chinese.id,
            type="essay",
            stem_html="请写一篇短文。",
            answer_mode="manual",
            standard_answer_json={"rubric": ["立意", "结构", "语言"]},
            score=20,
            version=1,
            status="published",
        )
        session.add(q)
        session.commit()
        return chinese.id, q.id


def test_subjective_submission_creates_pending_manual_review_and_final_score_regrades_attempt(client):
    subject_id, question_id = _seed_subjective_question(client)
    attempt_id = client.post('/api/attempts', json={"subject_id": subject_id, "mode": "practice"}).json()['id']
    saved = client.patch(
        f'/api/attempts/{attempt_id}/answers/{question_id}',
        json={"answer_json": {"value": "我的作文内容"}, "time_spent_seconds": 90},
    )
    assert saved.status_code == 200

    submitted = client.post(f'/api/attempts/{attempt_id}/submit')
    assert submitted.status_code == 200
    assert submitted.json()['status'] == 'submitted'
    assert submitted.json()['answers'][0]['grading_status'] == 'pending_manual'

    pending = client.get('/api/admin/reviews/pending')
    assert pending.status_code == 200
    assert len(pending.json()) == 1
    item = pending.json()[0]
    assert item['answer_id'] == saved.json()['id']
    assert item['question']['stem_html'] == '请写一篇短文。'
    assert item['max_score'] == 20

    reviewed = client.post(
        f"/api/admin/reviews/{item['answer_id']}",
        json={"suggested_score": 14, "final_score": 16, "comment": "结构完整，论据可加强。", "rubric_json": {"结构": 6, "语言": 5, "立意": 5}},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()['final_score'] == 16
    assert reviewed.json()['status'] == 'reviewed'

    attempt = client.get(f'/api/attempts/{attempt_id}').json()
    assert attempt['status'] == 'graded'
    assert attempt['score'] == 16
    assert attempt['max_score'] == 20
    assert attempt['answers'][0]['final_score'] == 16
    assert attempt['answers'][0]['grading_status'] == 'reviewed'


def test_manual_review_rejects_score_above_question_max(client):
    subject_id, question_id = _seed_subjective_question(client)
    attempt_id = client.post('/api/attempts', json={"subject_id": subject_id, "mode": "practice"}).json()['id']
    client.patch(f'/api/attempts/{attempt_id}/answers/{question_id}', json={"answer_json": {"value": "作文"}})
    client.post(f'/api/attempts/{attempt_id}/submit')
    answer_id = client.get('/api/admin/reviews/pending').json()[0]['answer_id']

    response = client.post(f'/api/admin/reviews/{answer_id}', json={"final_score": 21, "comment": "越界"})

    assert response.status_code == 400
    assert response.json()['detail'] == 'final_score must be between 0 and 20.0'
