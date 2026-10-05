import time
from unittest.mock import MagicMock

import pytest
from app.routes import server_control as routes


@pytest.fixture
def control_client(client, monkeypatch):
    with client.session_transaction() as state:
        state.update(authenticated=True, pin_verified=True, csrf_token="csrf", control_session="owner")
    routes._pending.clear()
    monkeypatch.setattr(routes, "target", lambda sid: ({"id": sid, "name": "Test", "ip_address": "192.0.2.1"},
        {"ip": "192.0.2.1", "port": 22, "user": "root", "password": "fixture"}))
    return client


def post(client, action, body, server="one"):
    return client.post(f"/api/servers/{server}/control/{action}", json=body, headers={"X-CSRF-Token": "csrf"})


def make_plan(client, monkeypatch):
    monkeypatch.setattr(routes, "invoke", lambda *a: {"hostname": "test-vps", "plan_hash": "a" * 64})
    return post(client, "plan", dict(component="vless", action="restart", instance="xray.service", runtime="systemd")).get_json()["ticket"]


def test_auth_and_csrf(client, control_client):
    assert control_client.post('/api/servers/one/control/discover', json={}).status_code == 403
    with client.session_transaction() as state:
        state.clear()
    assert post(client, "discover", {}).status_code == 401


def test_page(control_client):
    result = control_client.get('/servers/one/control')
    assert result.status_code == 200
    assert result.headers['Cache-Control'] == 'no-store'
    assert b'control-refresh' in result.data
    assert b'/api/monitoring/one/services-stats' in result.data
    assert b'/api/server/one/stats' in result.data
    assert b'control-protocols' in result.data


@pytest.mark.parametrize('component', ['anytls', 'tuic', 'xhttp', 'vless', 'hysteria2'])
def test_configuration_plan_and_apply_use_saved_change(control_client, monkeypatch, component):
    plan = {'hostname': 'test-vps', 'plan_hash': 'a' * 64}
    run = MagicMock(return_value=plan)
    monkeypatch.setattr(routes, 'invoke', run)
    body = {'action': 'configure', 'component': component, 'source_id': 'b'*64,
            'revision': 'c'*64, 'change': {'kind': 'add_client', 'name': 'alice'}}
    response = post(control_client, 'plan', body)
    assert response.status_code == 200
    ticket = response.get_json()['ticket']
    run.return_value = {'success': True}
    response = post(control_client, 'apply', {'ticket': ticket, 'confirmation': 'test-vps',
                     'change': {'kind': 'remove_client', 'name': 'bob'}})
    assert response.status_code == 200
    assert run.call_args.args[1]['change'] == body['change']
    assert run.call_args.args[1]['component'] == component
    assert post(control_client, 'apply', {'ticket': ticket, 'confirmation': 'test-vps'}).status_code == 409


def test_configuration_invalid_change_never_calls_ssh(control_client, monkeypatch):
    run = MagicMock()
    monkeypatch.setattr(routes, 'invoke', run)
    body = {'action': 'configure', 'component': 'anytls', 'source_id': 'b'*64,
            'revision': 'c'*64, 'change': {'kind': 'port', 'port': True}}
    assert post(control_client, 'plan', body).status_code == 400
    run.assert_not_called()


def test_configuration_blocker_is_explained(control_client, monkeypatch):
    monkeypatch.setattr(routes, 'invoke', lambda *a: {'success': False, 'error': 'bot_running'})
    body = {'action': 'configure', 'component': 'anytls', 'source_id': 'b'*64,
            'revision': 'c'*64, 'change': {'kind': 'port', 'port': 8443}}
    response = post(control_client, 'plan', body)
    assert response.status_code == 409
    assert 'TelegramOnly' in response.get_json()['error']


def test_protocols_read_only_and_no_store(control_client, monkeypatch):
    run = MagicMock(return_value={'hostname': 'test-vps', 'protocols': []})
    monkeypatch.setattr(routes, 'invoke', run)
    response = post(control_client, 'protocols', {'path': '/etc/shadow', 'action': 'write'})
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    assert run.call_args.args[1] == {'operation': 'protocols'}
    assert control_client.post('/api/servers/one/control/protocols', json={}).status_code == 403


def test_client_export_requires_csrf_and_no_store(control_client, monkeypatch):
    body = {'component':'anytls','source_id':'a'*64,'revision':'b'*64,'index':0}
    run = MagicMock(return_value={'profile':'anytls://fixture@example.com:443','format':'uri'})
    monkeypatch.setattr(routes, 'invoke', run)
    assert control_client.post('/api/servers/one/control/clients/export', json=body).status_code == 403
    run.assert_not_called()
    response = post(control_client, 'clients/export', body)
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    assert run.call_args.args[1]['operation'] == 'export_client'
    body['index'] = True
    assert post(control_client, 'clients/export', body).status_code == 400


@pytest.mark.parametrize("body", [[], None, {}, {"component": "vless", "runtime": "systemd", "instance": "xray.service", "action": "exec"}])
def test_invalid_plan(control_client, monkeypatch, body):
    run = MagicMock()
    monkeypatch.setattr(routes, 'invoke', run)
    assert post(control_client, 'plan', body).status_code == 400
    run.assert_not_called()


@pytest.mark.parametrize('change', ['server', 'owner', 'expiry', 'hostname'])
def test_plan_binding(control_client, monkeypatch, change):
    ticket = make_plan(control_client, monkeypatch)
    if change == 'owner':
        with control_client.session_transaction() as state:
            state['control_session'] = 'another'
    if change == 'expiry':
        routes._pending[ticket]['time'] = time.monotonic() - 301
    run = MagicMock()
    monkeypatch.setattr(routes, 'invoke', run)
    response = post(control_client, 'apply', {'ticket': ticket, 'confirmation': 'wrong' if change == 'hostname' else 'test-vps'}, 'two' if change == 'server' else 'one')
    assert response.status_code in (400, 409)
    run.assert_not_called()


def test_apply_uses_saved_operation_once(control_client, monkeypatch):
    ticket = make_plan(control_client, monkeypatch)
    run = MagicMock(return_value={'success': True})
    monkeypatch.setattr(routes, 'invoke', run)
    body = {'ticket': ticket, 'confirmation': 'test-vps', 'action': 'stop', 'instance': 'ssh.service'}
    assert post(control_client, 'apply', body).status_code == 200
    assert run.call_args.args[1]['action'] == 'restart'
    assert run.call_args.args[1]['instance'] == 'xray.service'
    assert post(control_client, 'apply', body).status_code == 409
    assert run.call_count == 1


def test_uncertain_result_consumes_plan_and_hides_exception(control_client, monkeypatch):
    ticket = make_plan(control_client, monkeypatch)
    monkeypatch.setattr(routes, 'invoke', MagicMock(side_effect=RuntimeError('secret-marker')))
    body = {'ticket': ticket, 'confirmation': 'test-vps'}
    response = post(control_client, 'apply', body)
    assert response.status_code == 502
    assert b'secret-marker' not in response.data
    assert post(control_client, 'apply', body).status_code == 409
