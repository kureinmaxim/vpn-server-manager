from unittest.mock import Mock

from app.routes import api


def test_brief_has_its_own_limit_after_polling(client, monkeypatch):
    with client.session_transaction() as state:
        state.update(authenticated=True, pin_verified=True)
    ssh = Mock()
    ssh.get_security_brief.return_value = {'summary': 'ok', 'prompt': 'prompt text'}
    monkeypatch.setattr(api.registry, 'get', lambda name: ssh if name == 'ssh' else Mock())
    monkeypatch.setattr(api, '_get_server_ssh_credentials', lambda server_id, manager: (
        {'id': server_id, 'name': 'Test'}, {'ip': '192.0.2.1', 'port': 22, 'user': 'root', 'password': 'x'}))
    api.rate_limiter.requests.clear()
    api.brief_limiter.requests.clear()
    try:
        # Опросы страницы съели общий лимит: кнопка разбора всё равно работает.
        while api.rate_limiter.is_allowed('server_one'):
            pass
        response = client.get('/api/monitoring/one/security-brief')
        assert response.status_code == 200 and response.json['data']['prompt'] == 'prompt text'
        while api.brief_limiter.is_allowed('server_one'):
            pass
        response = client.get('/api/monitoring/one/security-brief')
        assert response.status_code == 429 and 'Rate limit' not in response.json['error']
    finally:
        api.rate_limiter.requests.clear()
        api.brief_limiter.requests.clear()
