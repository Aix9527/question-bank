import sys

from fastapi.testclient import TestClient


def test_admin_token_protects_admin_routes_but_not_learner_routes(tmp_path, monkeypatch):
    monkeypatch.setenv('QUESTION_BANK_DATABASE_URL', f"sqlite:///{tmp_path / 'auth.db'}")
    monkeypatch.setenv('QUESTION_BANK_ADMIN_TOKEN', 'secret-token')
    for name in list(sys.modules):
        if name == 'app' or name.startswith('app.'):
            del sys.modules[name]

    from app.main import create_app

    with TestClient(create_app()) as client:
        assert client.get('/api/subjects').status_code == 200
        assert client.get('/api/admin/papers').status_code == 401
        assert client.get('/api/admin/papers', headers={'X-Admin-Token': 'wrong'}).status_code == 401
        assert client.get('/api/admin/papers', headers={'X-Admin-Token': 'secret-token'}).status_code == 200
