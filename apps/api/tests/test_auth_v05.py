import sys

from fastapi.testclient import TestClient


def _auth_client(tmp_path, monkeypatch):
    monkeypatch.setenv('QUESTION_BANK_DATABASE_URL', f"sqlite:///{tmp_path / 'auth-v05.db'}")
    monkeypatch.setenv('QUESTION_BANK_AUTH_REQUIRED', 'true')
    monkeypatch.setenv('QUESTION_BANK_BOOTSTRAP_ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('QUESTION_BANK_BOOTSTRAP_ADMIN_PASSWORD', 'admin-pass-123')
    monkeypatch.delenv('QUESTION_BANK_ADMIN_TOKEN', raising=False)
    for name in list(sys.modules):
        if name == 'app' or name.startswith('app.'):
            del sys.modules[name]
    from app.main import create_app
    return TestClient(create_app())


def test_auth_required_bootstrap_admin_login_and_logout(tmp_path, monkeypatch):
    with _auth_client(tmp_path, monkeypatch) as client:
        assert client.get('/api/subjects').status_code == 200
        assert client.get('/api/auth/me').status_code == 401

        bad = client.post('/api/auth/login', json={'username': 'admin', 'password': 'wrong-pass'})
        assert bad.status_code == 401

        login = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin-pass-123'})
        assert login.status_code == 200
        body = login.json()
        assert body['user']['username'] == 'admin'
        assert body['user']['id'] == 1
        assert body['user']['role'] == 'admin'
        token = body['token']

        headers = {'Authorization': f'Bearer {token}'}
        me = client.get('/api/auth/me', headers=headers)
        assert me.status_code == 200
        assert me.json()['role'] == 'admin'
        assert client.get('/api/admin/papers', headers=headers).status_code == 200

        logout = client.post('/api/auth/logout', headers=headers)
        assert logout.status_code == 204
        assert client.get('/api/auth/me', headers=headers).status_code == 401


def test_admin_can_create_learner_and_learner_cannot_use_admin_routes(tmp_path, monkeypatch):
    with _auth_client(tmp_path, monkeypatch) as client:
        admin_login = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin-pass-123'}).json()
        admin_headers = {'Authorization': f"Bearer {admin_login['token']}"}

        created = client.post(
            '/api/admin/users',
            headers=admin_headers,
            json={'username': 'alice', 'password': 'alice-pass-123', 'display_name': 'Alice', 'role': 'learner'},
        )
        assert created.status_code == 201
        learner = created.json()
        assert learner['username'] == 'alice'
        assert learner['role'] == 'learner'
        assert learner['enabled'] is True

        duplicate = client.post(
            '/api/admin/users',
            headers=admin_headers,
            json={'username': 'alice', 'password': 'another-pass-123', 'role': 'learner'},
        )
        assert duplicate.status_code == 409

        login = client.post('/api/auth/login', json={'username': 'alice', 'password': 'alice-pass-123'})
        assert login.status_code == 200
        learner_headers = {'Authorization': f"Bearer {login.json()['token']}"}
        assert client.get('/api/admin/papers', headers=learner_headers).status_code == 403
        assert client.get('/api/auth/me', headers=learner_headers).json()['username'] == 'alice'

        users = client.get('/api/admin/users', headers=admin_headers)
        assert users.status_code == 200
        assert {'admin', 'alice'} <= {item['username'] for item in users.json()}


def test_local_mode_keeps_legacy_user_one_without_login(client):
    me = client.get('/api/auth/me')
    assert me.status_code == 200
    assert me.json()['id'] == 1
    assert me.json()['username'] == 'local'
    assert me.json()['role'] == 'learner'


def test_expired_session_is_rejected(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, timezone

    with _auth_client(tmp_path, monkeypatch) as client:
        login = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin-pass-123'}).json()
        token = login['token']
        from app.models.user import UserSession
        with client.app.state.session_factory() as session:
            row = session.scalar(__import__('sqlalchemy').select(UserSession).order_by(UserSession.id.desc()))
            row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            session.commit()
        assert client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401


def test_enabling_auth_promotes_legacy_user_one_and_preserves_history(tmp_path, monkeypatch):
    db_path = tmp_path / 'upgrade-v04.db'
    monkeypatch.setenv('QUESTION_BANK_DATABASE_URL', f'sqlite:///{db_path}')
    monkeypatch.setenv('QUESTION_BANK_AUTH_REQUIRED', 'false')
    monkeypatch.delenv('QUESTION_BANK_BOOTSTRAP_ADMIN_USERNAME', raising=False)
    monkeypatch.delenv('QUESTION_BANK_BOOTSTRAP_ADMIN_PASSWORD', raising=False)
    for name in list(sys.modules):
        if name == 'app' or name.startswith('app.'):
            del sys.modules[name]
    from app.main import create_app
    from app.models.core import Subject
    from app.models.question_bank import Question
    from sqlalchemy import select

    with TestClient(create_app()) as local:
        with local.app.state.session_factory() as session:
            math = session.scalar(select(Subject).where(Subject.code == 'math'))
            q = Question(subject_id=math.id, type='single_choice', stem_html='1+1=?', answer_mode='exact', standard_answer_json={'value':'B'}, score=5, status='published', version=1)
            session.add(q); session.commit(); subject_id, question_id = math.id, q.id
        attempt = local.post('/api/attempts', json={'subject_id': subject_id, 'mode': 'practice'}).json()
        local.patch(f"/api/attempts/{attempt['id']}/answers/{question_id}", json={'answer_json': {'value': 'B'}})
        local.post(f"/api/attempts/{attempt['id']}/submit")
        assert len(local.get('/api/me/history').json()) == 1

    monkeypatch.setenv('QUESTION_BANK_AUTH_REQUIRED', 'true')
    monkeypatch.setenv('QUESTION_BANK_BOOTSTRAP_ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('QUESTION_BANK_BOOTSTRAP_ADMIN_PASSWORD', 'admin-pass-123')
    for name in list(sys.modules):
        if name == 'app' or name.startswith('app.'):
            del sys.modules[name]
    from app.main import create_app as create_auth_app
    with TestClient(create_auth_app()) as deployed:
        login = deployed.post('/api/auth/login', json={'username': 'admin', 'password': 'admin-pass-123'})
        assert login.status_code == 200
        assert login.json()['user']['id'] == 1
        headers = {'Authorization': f"Bearer {login.json()['token']}"}
        history = deployed.get('/api/me/history', headers=headers)
        assert history.status_code == 200
        assert len(history.json()) == 1
