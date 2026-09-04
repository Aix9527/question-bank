import sys

from fastapi.testclient import TestClient


def _auth_client(tmp_path, monkeypatch):
    monkeypatch.setenv('QUESTION_BANK_DATABASE_URL', f"sqlite:///{tmp_path / 'auth-register-password.db'}")
    monkeypatch.setenv('QUESTION_BANK_AUTH_REQUIRED', 'true')
    monkeypatch.setenv('QUESTION_BANK_BOOTSTRAP_ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('QUESTION_BANK_BOOTSTRAP_ADMIN_PASSWORD', 'admin-pass-123')
    monkeypatch.delenv('QUESTION_BANK_ADMIN_TOKEN', raising=False)
    for name in list(sys.modules):
        if name == 'app' or name.startswith('app.'):
            del sys.modules[name]
    from app.main import create_app
    return TestClient(create_app())


def test_public_register_creates_learner_and_returns_session(tmp_path, monkeypatch):
    with _auth_client(tmp_path, monkeypatch) as client:
        registered = client.post('/api/auth/register', json={
            'username': 'bob',
            'password': 'bob-pass-123',
            'display_name': 'Bob 同学',
        })
        assert registered.status_code == 201
        body = registered.json()
        assert body['user']['username'] == 'bob'
        assert body['user']['role'] == 'learner'
        assert body['user']['enabled'] is True
        headers = {'Authorization': f"Bearer {body['token']}"}
        me = client.get('/api/auth/me', headers=headers)
        assert me.status_code == 200
        assert me.json()['username'] == 'bob'

        duplicate = client.post('/api/auth/register', json={'username': 'bob', 'password': 'x-123456'})
        assert duplicate.status_code == 409

        bad_username = client.post('/api/auth/register', json={'username': 'bad name!', 'password': 'x-123456'})
        assert bad_username.status_code == 422

        empty_password = client.post('/api/auth/register', json={'username': 'carol', 'password': ''})
        assert empty_password.status_code == 422

        # 注册账号只能以学习身份使用管理员路由
        assert client.get('/api/admin/users', headers=headers).status_code == 403


def test_change_password_revokes_other_sessions_only(tmp_path, monkeypatch):
    with _auth_client(tmp_path, monkeypatch) as client:
        registered = client.post('/api/auth/register', json={
            'username': 'dave',
            'password': 'old-pass-123',
            'display_name': 'Dave',
        }).json()
        token_a = registered['token']
        login_b = client.post('/api/auth/login', json={'username': 'dave', 'password': 'old-pass-123'}).json()
        token_b = login_b['token']

        headers_a = {'Authorization': f'Bearer {token_a}'}
        headers_b = {'Authorization': f'Bearer {token_b}'}
        assert client.get('/api/auth/me', headers=headers_a).status_code == 200
        assert client.get('/api/auth/me', headers=headers_b).status_code == 200

        # 旧密码错误 → 400，密码不变
        wrong_old = client.post('/api/auth/change-password', headers=headers_a, json={
            'old_password': 'wrong-old', 'new_password': 'new-pass-123',
        })
        assert wrong_old.status_code == 400
        assert client.post('/api/auth/login', json={'username': 'dave', 'password': 'old-pass-123'}).status_code == 200

        # 新密码为空 → 422（schema 层 min_length=1 拦截）
        empty_new = client.post('/api/auth/change-password', headers=headers_a, json={
            'old_password': 'old-pass-123', 'new_password': '',
        })
        assert empty_new.status_code == 422

        # 正确修改 → 204，当前会话保留、其它会话失效
        changed = client.post('/api/auth/change-password', headers=headers_a, json={
            'old_password': 'old-pass-123', 'new_password': 'new-pass-123',
        })
        assert changed.status_code == 204
        assert client.get('/api/auth/me', headers=headers_a).status_code == 200
        assert client.get('/api/auth/me', headers=headers_b).status_code == 401
        assert client.post('/api/auth/login', json={'username': 'dave', 'password': 'old-pass-123'}).status_code == 401
        assert client.post('/api/auth/login', json={'username': 'dave', 'password': 'new-pass-123'}).status_code == 200


def test_admin_can_reset_learner_password(tmp_path, monkeypatch):
    with _auth_client(tmp_path, monkeypatch) as client:
        admin_login = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin-pass-123'}).json()
        admin_headers = {'Authorization': f"Bearer {admin_login['token']}"}

        registered = client.post('/api/auth/register', json={'username': 'erin', 'password': 'first-pass-1'}).json()
        learner_id = registered['user']['id']

        reset = client.patch(
            f'/api/admin/users/{learner_id}',
            headers=admin_headers,
            json={'password': 'reset-pass-99'},
        )
        assert reset.status_code == 200
        assert client.post('/api/auth/login', json={'username': 'erin', 'password': 'first-pass-1'}).status_code == 401
        assert client.post('/api/auth/login', json={'username': 'erin', 'password': 'reset-pass-99'}).status_code == 200

        # 管理员空密码被拒绝
        reset_empty = client.patch(
            f'/api/admin/users/{learner_id}',
            headers=admin_headers,
            json={'role': 'admin', 'password': ''},
        )
        assert reset_empty.status_code == 400
