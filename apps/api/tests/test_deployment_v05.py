from pathlib import Path


def test_health_endpoints_report_live_and_database_ready(client):
    live = client.get('/api/health/live')
    ready = client.get('/api/health/ready')
    assert live.status_code == 200
    assert live.json() == {'status': 'ok'}
    assert ready.status_code == 200
    assert ready.json()['status'] == 'ready'
    assert ready.json()['database'] == 'ok'


def test_compose_defaults_to_auth_required_and_readiness_healthcheck():
    root = Path(__file__).resolve().parents[3]
    text = (root / 'docker-compose.yml').read_text(encoding='utf-8')
    assert 'QUESTION_BANK_AUTH_REQUIRED: ${QUESTION_BANK_AUTH_REQUIRED:-true}' in text
    assert 'QUESTION_BANK_BOOTSTRAP_ADMIN_USERNAME' in text
    assert 'QUESTION_BANK_BOOTSTRAP_ADMIN_PASSWORD' in text
    assert '/api/health/ready' in text
    assert 'QUESTION_BANK_ADMIN_TOKEN: ${QUESTION_BANK_ADMIN_TOKEN:?' not in text


def test_production_compose_keeps_api_private_and_terminates_tls_at_caddy():
    root = Path(__file__).resolve().parents[3]
    text = (root / 'docker-compose.prod.yml').read_text(encoding='utf-8')
    assert 'caddy:' in text
    assert 'QUESTION_BANK_COOKIE_SECURE: "true"' in text
    assert '8000:8000' not in text
    caddy = (root / 'deploy/Caddyfile').read_text(encoding='utf-8')
    assert '{$QUESTION_BANK_DOMAIN}' in caddy
    assert 'reverse_proxy web:3000' in caddy
