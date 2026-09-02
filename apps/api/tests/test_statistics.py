from sqlalchemy import select


def _seed_two_subjects(client):
    from app.models.core import Subject
    from app.models.question_bank import Paper, Question

    with client.app.state.session_factory() as session:
        math = session.scalar(select(Subject).where(Subject.code == 'math'))
        english = session.scalar(select(Subject).where(Subject.code == 'english'))
        paper = Paper(subject_id=math.id, title='数学演示卷', paper_type='mock', total_score=10, status='published', version=1)
        q_math = Question(subject_id=math.id, type='single_choice', stem_html='3+3=?', answer_mode='exact', standard_answer_json={'value':'B'}, score=5, knowledge_points=['基础运算'], version=1, status='published')
        q_eng = Question(subject_id=english.id, type='fill_blank', stem_html='hello 的中文', answer_mode='normalized_text', standard_answer_json={'value':'你好'}, score=5, knowledge_points=['词汇'], version=1, status='published')
        session.add_all([paper, q_math, q_eng])
        session.commit()
        return math.id, english.id, paper.id, q_math.id, q_eng.id


def _attempt(client, subject_id, question_id, answer, paper_id=None):
    attempt_id = client.post('/api/attempts', json={"subject_id": subject_id, "paper_id": paper_id, "mode": "practice"}).json()['id']
    client.patch(f'/api/attempts/{attempt_id}/answers/{question_id}', json={"answer_json": {"value": answer}, "time_spent_seconds": 4})
    return client.post(f'/api/attempts/{attempt_id}/submit').json()


def test_history_and_statistics_aggregate_by_subject_type_and_knowledge_point(client):
    math_id, english_id, paper_id, q_math, q_eng = _seed_two_subjects(client)
    math_attempt = _attempt(client, math_id, q_math, 'B', paper_id=paper_id)
    _attempt(client, english_id, q_eng, '错误')

    history = client.get('/api/me/history')
    assert history.status_code == 200
    assert len(history.json()) == 2
    math_history = next(item for item in history.json() if item['id'] == math_attempt['id'])
    assert math_history['subject_code'] == 'math'
    assert math_history['paper_title'] == '数学演示卷'
    assert math_history['score_rate'] == 1.0

    stats = client.get('/api/me/statistics')
    assert stats.status_code == 200
    body = stats.json()
    assert body['totals']['attempts'] == 2
    assert body['totals']['objective_answers'] == 2
    assert body['totals']['correct_answers'] == 1
    assert body['totals']['accuracy'] == 0.5
    assert body['totals']['wrong_questions'] == 1
    assert body['activity']['last_7_days_answers'] == 2
    assert body['activity']['last_30_days_answers'] == 2

    by_subject = {item['code']: item for item in body['subjects']}
    assert by_subject['math']['accuracy'] == 1.0
    assert by_subject['english']['accuracy'] == 0.0

    by_type = {item['question_type']: item for item in body['question_type_accuracy']}
    assert by_type['single_choice']['accuracy'] == 1.0
    assert by_type['fill_blank']['accuracy'] == 0.0

    by_kp = {item['knowledge_point']: item for item in body['knowledge_point_accuracy']}
    assert by_kp['基础运算']['accuracy'] == 1.0
    assert by_kp['词汇']['accuracy'] == 0.0
    assert len(body['exam_trend']) == 2
