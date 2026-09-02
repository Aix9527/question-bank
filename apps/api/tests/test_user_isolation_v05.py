import sys

from fastapi.testclient import TestClient
from sqlalchemy import select


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv('QUESTION_BANK_DATABASE_URL', f"sqlite:///{tmp_path / 'isolation.db'}")
    monkeypatch.setenv('QUESTION_BANK_AUTH_REQUIRED', 'true')
    monkeypatch.setenv('QUESTION_BANK_BOOTSTRAP_ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('QUESTION_BANK_BOOTSTRAP_ADMIN_PASSWORD', 'admin-pass-123')
    for name in list(sys.modules):
        if name == 'app' or name.startswith('app.'):
            del sys.modules[name]
    from app.main import create_app
    return TestClient(create_app())


def _headers(client, username, password):
    response = client.post('/api/auth/login', json={'username': username, 'password': password})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['token']}"}


def _seed_question(client):
    from app.models.core import Subject
    from app.models.question_bank import Question
    with client.app.state.session_factory() as session:
        math = session.scalar(select(Subject).where(Subject.code == 'math'))
        q = Question(
            subject_id=math.id,
            type='single_choice',
            stem_html='5+5=?',
            answer_mode='exact',
            standard_answer_json={'value': 'B'},
            score=5,
            knowledge_points=['基础运算'],
            version=1,
            status='published',
        )
        session.add(q)
        session.commit()
        return math.id, q.id


def test_learner_data_is_scoped_and_attempt_ids_cannot_cross_users(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        admin = _headers(client, 'admin', 'admin-pass-123')
        for username in ('alice', 'bob'):
            response = client.post(
                '/api/admin/users', headers=admin,
                json={'username': username, 'password': f'{username}-pass-123', 'role': 'learner'},
            )
            assert response.status_code == 201
        alice = _headers(client, 'alice', 'alice-pass-123')
        bob = _headers(client, 'bob', 'bob-pass-123')
        subject_id, question_id = _seed_question(client)

        attempt = client.post('/api/attempts', headers=alice, json={'subject_id': subject_id, 'mode': 'practice'})
        assert attempt.status_code == 201
        attempt_id = attempt.json()['id']
        assert attempt.json()['user_id'] != 1
        assert client.patch(
            f'/api/attempts/{attempt_id}/answers/{question_id}', headers=alice,
            json={'answer_json': {'value': 'A'}, 'time_spent_seconds': 3},
        ).status_code == 200
        assert client.post(f'/api/attempts/{attempt_id}/submit', headers=alice).status_code == 200
        assert client.post(f'/api/questions/{question_id}/favorite', headers=alice).status_code == 201

        assert client.get(f'/api/attempts/{attempt_id}', headers=bob).status_code == 404
        assert client.patch(
            f'/api/attempts/{attempt_id}/answers/{question_id}', headers=bob,
            json={'answer_json': {'value': 'B'}},
        ).status_code == 404
        assert client.post(f'/api/attempts/{attempt_id}/submit', headers=bob).status_code == 404
        assert client.get('/api/me/wrong-questions', headers=bob).json() == []
        assert client.get('/api/me/favorites', headers=bob).json() == []
        assert client.get('/api/me/history', headers=bob).json() == []
        assert client.get('/api/me/statistics', headers=bob).json()['totals']['attempts'] == 0

        assert len(client.get('/api/me/wrong-questions', headers=alice).json()) == 1
        assert len(client.get('/api/me/favorites', headers=alice).json()) == 1
        assert len(client.get('/api/me/history', headers=alice).json()) == 1
