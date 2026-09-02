from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCES = ROOT / 'data' / 'source_papers'


def _publish_real_docx(client, *, filename: str, subject_code: str) -> dict:
    payload = (SOURCES / filename).read_bytes()
    uploaded = client.post(
        '/api/admin/imports/docx',
        data={'subject_code': subject_code},
        files={'file': (filename, payload, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')},
    )
    assert uploaded.status_code in {200, 201}
    job = uploaded.json()
    assert job['blocking_warning_count'] == 0
    published = client.post(f"/api/admin/imports/{job['id']}/publish")
    assert published.status_code == 200
    return client.get(f"/api/papers/{published.json()['paper_id']}").json()


def test_real_math_wrong_review_and_real_chinese_manual_review_flow(client):
    math_paper = _publish_real_docx(
        client,
        filename='成考高起专数学（文）模拟题一.docx',
        subject_code='math',
    )
    choice = next(q for section in math_paper['sections'] for q in section['questions'] if q['type'] == 'single_choice')
    correct = choice['standard_answer_json'].get('value') or choice['standard_answer_json'].get('answer')
    wrong = next(option['label'] for option in choice['options'] if option['label'] != correct)

    attempt = client.post('/api/attempts', json={
        'subject_id': math_paper['subject_id'], 'paper_id': math_paper['id'], 'mode': 'practice',
    }).json()
    client.patch(
        f"/api/attempts/{attempt['id']}/answers/{choice['id']}",
        json={'answer_json': {'value': wrong}, 'time_spent_seconds': 1},
    )
    submitted = client.post(f"/api/attempts/{attempt['id']}/submit").json()
    assert submitted['score'] == 0
    wrong_item = next(item for item in client.get('/api/me/wrong-questions').json() if item['question_id'] == choice['id'])
    assert wrong_item['state'] == 'pending'

    for expected_state in ('learning', 'mastered'):
        review_attempt = client.post('/api/me/wrong-questions/review-attempt', json={'question_ids': [choice['id']]}).json()['attempt']
        client.patch(
            f"/api/attempts/{review_attempt['id']}/answers/{choice['id']}",
            json={'answer_json': {'value': correct}, 'time_spent_seconds': 1},
        )
        client.post(f"/api/attempts/{review_attempt['id']}/submit")
        current = next(item for item in client.get('/api/me/wrong-questions').json() if item['question_id'] == choice['id'])
        assert current['state'] == expected_state

    chinese_paper = _publish_real_docx(
        client,
        filename='成考高起专语文 模拟1.docx',
        subject_code='chinese',
    )
    manual = next(q for section in chinese_paper['sections'] for q in section['questions'] if q['answer_mode'] == 'manual')
    chinese_attempt = client.post('/api/attempts', json={
        'subject_id': chinese_paper['subject_id'], 'paper_id': chinese_paper['id'], 'mode': 'practice',
    }).json()
    client.patch(
        f"/api/attempts/{chinese_attempt['id']}/answers/{manual['id']}",
        json={'answer_json': {'value': '这是一份真实卷主观题测试答案。'}, 'time_spent_seconds': 10},
    )
    pending_attempt = client.post(f"/api/attempts/{chinese_attempt['id']}/submit").json()
    assert pending_attempt['status'] == 'submitted'
    pending = client.get('/api/admin/reviews/pending').json()
    review = next(item for item in pending if item['question_id'] == manual['id'])
    reviewed = client.post(
        f"/api/admin/reviews/{review['answer_id']}",
        json={'suggested_score': None, 'final_score': manual['score'] / 2, 'comment': '真实卷批改走查', 'rubric_json': None},
    )
    assert reviewed.status_code == 200
    graded = client.get(f"/api/attempts/{chinese_attempt['id']}").json()
    assert graded['status'] == 'graded'
    assert graded['score'] == manual['score'] / 2
