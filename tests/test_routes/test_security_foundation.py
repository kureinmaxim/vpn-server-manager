"""Raw clients deliberately bypass the browser CSRF fixture."""
from pathlib import Path

import pytest
from app.routes import api


def token(client):
    client.get('/locked')
    with client.session_transaction() as state:
        return state['csrf_token']


def test_raw_post_requires_csrf_and_rejects_unicode_token(app):
    client = app.test_client()
    value = token(client)
    for headers in ({}, {'X-CSRF-Token': 'wrong'}, {'X-CSRF-Token': 'токен'}):
        assert client.post('/pin/login_ajax', json={'pin': '1234'}, headers=headers).status_code == 403
    assert client.post('/pin/login_ajax', json={'pin': 'wrong'},
                       headers={'X-CSRF-Token': value}).status_code == 401


def test_pin_limit_survives_new_cookies_and_covers_legacy_route(app, monkeypatch):
    monkeypatch.setattr(api, '_get_current_pin', lambda: '5678')
    for i in range(10):
        client = app.test_client()
        value = token(client)
        assert client.post('/pin/login_ajax', json={'pin': 'wrong'},
                           headers={'X-CSRF-Token': value}).status_code == 401
    client = app.test_client()
    assert client.post('/verify_pin', data={'pin': '5678'},
                       headers={'X-CSRF-Token': token(client)}).status_code == 429


def test_legacy_route_does_not_accept_default_when_pin_changed(app, monkeypatch):
    monkeypatch.setattr(api, '_get_current_pin', lambda: '5678')
    client = app.test_client()
    client.post('/verify_pin', data={'pin': '1234'}, headers={'X-CSRF-Token': token(client)})
    with client.session_transaction() as state:
        assert not state.get('authenticated')


@pytest.mark.parametrize('path', ['/api/monitoring/demo/install', '/api/monitoring/demo/uninstall', '/shutdown'])
def test_mutations_are_not_get_routes(app, path):
    client = app.test_client()
    with client.session_transaction() as state:
        state.update(authenticated=True, pin_verified=True)
    assert client.get(path).status_code == 405
    assert client.post(path).status_code == 403


def test_cross_origin_and_untrusted_host_are_rejected(app):
    client = app.test_client()
    value = token(client)
    assert client.post('/pin/login_ajax', json={'pin': '1234'},
        headers={'X-CSRF-Token': value, 'Origin': 'https://example.com'}).status_code == 403
    assert client.get('/', base_url='http://attacker.example').status_code == 400


def test_pin_not_logged(app, monkeypatch, caplog):
    monkeypatch.setattr(api, '_get_current_pin', lambda: 'other')
    client = app.test_client()
    client.post('/pin/login_ajax', json={'pin': 'CANARY-PIN-SECRET'},
                headers={'X-CSRF-Token': token(client)})
    assert 'CANARY-PIN-SECRET' not in caplog.text


def test_corrupt_config_never_authenticates_default_pin(app):
    path = Path(app.config['APP_DATA_DIR']) / 'config.json'
    path.write_text('{broken')
    client = app.test_client()
    value = token(client)
    assert client.post('/pin/login_ajax', json={'pin': '1234'},
                       headers={'X-CSRF-Token': value}).status_code == 500
    assert path.read_text() == '{broken'
    with client.session_transaction() as state:
        assert not state.get('authenticated')


def test_corrupt_inventory_shows_recovery_error_and_cannot_be_deleted(app):
    from cryptography.fernet import Fernet
    from app.services import registry
    from app.services.data_manager_service import DataManagerService
    manager = DataManagerService(Fernet.generate_key().decode(), app.config['APP_DATA_DIR'])
    path = Path(app.config['DATA_DIR']) / 'inventory.enc'
    path.write_bytes(b'corrupted-fixture')
    app.config['active_data_file'] = str(path)
    registry.register('data_manager', manager)
    client = app.test_client()
    with client.session_transaction() as state:
        state.update(authenticated=True, pin_verified=True, pin_authenticated=True)
    page = client.get('/')
    assert page.status_code == 409
    assert b'Writing is disabled' in page.data
    assert client.post('/delete_server/1').status_code == 403
    client.post('/delete_server/1', headers={'X-CSRF-Token': token(client)})
    assert path.read_bytes() == b'corrupted-fixture'
