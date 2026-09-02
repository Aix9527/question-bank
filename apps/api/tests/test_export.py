import io
import zipfile


def test_admin_export_json_and_csv_zip_include_learning_and_bank_data(client):
    subject = next(item for item in client.get('/api/subjects').json() if item['code'] == 'math')
    question = client.post('/api/admin/questions', json={
        'subject_code': 'math', 'type': 'single_choice', 'stem_html': '1+1=?',
        'answer_mode': 'exact', 'standard_answer_json': {'value': 'B'}, 'score': 5,
        'status': 'published',
        'options': [
            {'label': 'A', 'content_html': '1', 'order_index': 1},
            {'label': 'B', 'content_html': '2', 'order_index': 2},
        ],
    }).json()
    attempt = client.post('/api/attempts', json={'subject_id': subject['id'], 'paper_id': None, 'mode': 'practice'}).json()
    client.patch(
        f"/api/attempts/{attempt['id']}/answers/{question['id']}",
        json={'answer_json': {'value': 'A'}, 'time_spent_seconds': 3},
    )
    client.post(f"/api/attempts/{attempt['id']}/submit")

    exported = client.get('/api/admin/export?format=json')
    assert exported.status_code == 200
    assert 'attachment;' in exported.headers.get('content-disposition', '')
    body = exported.json()
    assert body['schema_version'] == 1
    assert len(body['question_bank']['questions']) == 1
    assert len(body['learning']['attempts']) == 1
    assert len(body['learning']['wrong_questions']) == 1

    csv_export = client.get('/api/admin/export?format=csv')
    assert csv_export.status_code == 200
    assert csv_export.headers['content-type'].startswith('application/zip')
    with zipfile.ZipFile(io.BytesIO(csv_export.content)) as archive:
        names = set(archive.namelist())
        assert {'questions.csv', 'attempts.csv', 'wrong_questions.csv'} <= names


def test_export_includes_sanitized_users_but_never_password_hashes_or_sessions(client):
    body = client.get('/api/admin/export?format=json').json()
    assert 'accounts' in body
    assert body['accounts']['users'][0]['username'] == 'local'
    assert 'password_hash' not in body['accounts']['users'][0]
    assert 'user_sessions' not in body['accounts']
