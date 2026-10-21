import json
import uuid
from unittest.mock import Mock

import pytest

from app.services import registry
from app.services.dns_mail import settings
from app.routes.api import load_check_limiter


@pytest.fixture
def diagnostic_client(client):
    with client.session_transaction() as session:
        session.update(authenticated=True, pin_verified=True, language='ru')
    manager = Mock()
    manager.load_servers.return_value = [{'id': 'demo', 'name': 'Demo', 'ip_address': '192.0.2.1',
        'ssh_credentials': {'user': 'operator', 'port': 2222, 'private_key': 'encrypted-key'}}]
    manager.decrypt_data.return_value = 'test-key'
    manager.get_active_data_path.return_value = 'unused.enc'
    registry.register('data_manager', manager)
    registry.register('ssh', Mock())
    load_check_limiter.requests.clear()
    yield client
    load_check_limiter.requests.clear()


def post(client, config=None, action='run'):
    client.get('/diagnostics/demo')
    with client.session_transaction() as session:
        token = session['diagnostics_token']
    return client.post('/diagnostics/demo', json={'action': action, 'config': config or settings({})},
                       headers={'X-Diagnostics-Token': token})


def test_auth_and_token_before_any_ssh(client, diagnostic_client):
    with diagnostic_client.session_transaction() as session:
        session.clear()
    assert diagnostic_client.post('/diagnostics/demo', json={}).status_code == 401
    with diagnostic_client.session_transaction() as session:
        session.update(authenticated=True, pin_verified=True)
    assert diagnostic_client.post('/diagnostics/demo', json={}).status_code == 403
    registry.get('ssh').get_connection_pooled.assert_not_called()


def test_saved_settings_use_existing_encrypted_store(diagnostic_client):
    response = post(diagnostic_client, settings({'mail_domain': 'mail.example.com'}), 'save')
    assert response.status_code == 200
    manager = registry.get('data_manager')
    servers, path = manager.save_servers.call_args.args
    assert path == 'unused.enc' and servers[0]['dns_mail_diagnostics']['mail_domain'] == 'mail.example.com'
    assert 'private_key' in servers[0]['ssh_credentials']
    registry.get('ssh').get_connection_pooled.assert_not_called()


def test_ssh_uses_profile_key_and_never_exposes_http_exception(diagnostic_client, monkeypatch, caplog):
    secret = 'https://example.com/' + uuid.uuid4().hex
    monkeypatch.setattr('app.routes.dns_mail.remote_probe', Mock(side_effect=RuntimeError(secret)))
    response = post(diagnostic_client)
    assert response.status_code == 502
    assert secret not in response.text + caplog.text
    registry.get('ssh').get_connection_pooled.assert_called_once_with(hostname='192.0.2.1',
        username='operator', port=2222, password='', key='test-key', key_passphrase='', connection_timeout=5)


def test_result_and_capacity_limit(diagnostic_client, monkeypatch):
    monkeypatch.setattr('app.routes.dns_mail.remote_probe', lambda *args: [])
    monkeypatch.setattr('app.routes.dns_mail.remember', lambda *args: None)
    response = post(diagnostic_client)
    assert response.status_code == 200 and response.headers['Cache-Control'] == 'no-store'
    slots = Mock()
    slots.acquire.return_value = False
    monkeypatch.setattr('app.routes.dns_mail._slots', slots)
    assert post(diagnostic_client).status_code == 429


def test_secret_urls_not_accepted_or_saved(diagnostic_client):
    response = post(diagnostic_client, dict(settings({}), doh_url='https://example.com/dns-query'), 'save')
    assert response.status_code == 400
    registry.get('data_manager').save_servers.assert_not_called()


def test_role_selection_and_page(diagnostic_client):
    response = diagnostic_client.get('/diagnostics/demo?role=chatmail')
    assert response.status_code == 200
    assert 'value="chatmail" selected' in response.text
    assert 'test-key' not in response.text and 'encrypted-key' not in response.text
