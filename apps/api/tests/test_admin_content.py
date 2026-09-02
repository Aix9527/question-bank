
def test_admin_question_crud_versions_and_archives(client):
    created = client.post('/api/admin/questions', json={
        'subject_code': 'math',
        'type': 'single_choice',
        'stem_html': '1 + 1 = ?',
        'material_html': None,
        'answer_mode': 'exact',
        'standard_answer_json': {'value': 'B'},
        'explanation_html': '基础加法',
        'score': 5,
        'difficulty': 'easy',
        'knowledge_points': ['基础计算'],
        'source': 'manual',
        'status': 'draft',
        'options': [
            {'label': 'A', 'content_html': '1', 'order_index': 1},
            {'label': 'B', 'content_html': '2', 'order_index': 2},
            {'label': 'C', 'content_html': '3', 'order_index': 3},
            {'label': 'D', 'content_html': '4', 'order_index': 4},
        ],
    })
    assert created.status_code == 201
    q = created.json()
    assert q['version'] == 1
    assert q['status'] == 'draft'
    assert [o['label'] for o in q['options']] == ['A', 'B', 'C', 'D']

    listed = client.get('/api/admin/questions?subject_code=math&status=draft')
    assert listed.status_code == 200
    assert [item['id'] for item in listed.json()] == [q['id']]

    updated = client.patch(f"/api/admin/questions/{q['id']}", json={
        'stem_html': '2 + 2 = ?',
        'standard_answer_json': {'value': 'C'},
        'status': 'published',
        'options': [
            {'label': 'A', 'content_html': '2', 'order_index': 1},
            {'label': 'B', 'content_html': '3', 'order_index': 2},
            {'label': 'C', 'content_html': '4', 'order_index': 3},
            {'label': 'D', 'content_html': '5', 'order_index': 4},
        ],
    })
    assert updated.status_code == 200
    body = updated.json()
    assert body['stem_html'] == '2 + 2 = ?'
    assert body['standard_answer_json'] == {'value': 'C'}
    assert body['version'] == 2
    assert body['status'] == 'published'

    archived = client.delete(f"/api/admin/questions/{q['id']}")
    assert archived.status_code == 200
    assert archived.json()['status'] == 'archived'
    assert archived.json()['version'] == 3


def test_admin_paper_crud_updates_metadata_and_archives(client):
    created = client.post('/api/admin/papers', json={
        'subject_code': 'chinese',
        'title': '自建语文练习卷',
        'paper_type': 'practice',
        'total_score': 100,
        'time_limit_minutes': 90,
        'status': 'draft',
    })
    assert created.status_code == 201
    paper = created.json()
    assert paper['version'] == 1

    updated = client.patch(f"/api/admin/papers/{paper['id']}", json={
        'title': '自建语文练习卷（修订）',
        'time_limit_minutes': 100,
        'status': 'published',
    })
    assert updated.status_code == 200
    assert updated.json()['version'] == 2
    assert updated.json()['title'].endswith('（修订）')

    listed = client.get('/api/admin/papers?subject_code=chinese&status=published')
    assert listed.status_code == 200
    assert any(item['id'] == paper['id'] for item in listed.json())

    archived = client.delete(f"/api/admin/papers/{paper['id']}")
    assert archived.status_code == 200
    assert archived.json()['status'] == 'archived'
    assert archived.json()['version'] == 3
