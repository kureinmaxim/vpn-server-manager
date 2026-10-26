from unittest.mock import Mock

import paramiko
import pytest

from app.routes import api
from app.routes.reset import RemoteConnectError

URL = '/api/monitoring/one/history-script'


@pytest.fixture
def history_client(client, monkeypatch):
    with client.session_transaction() as state:
        state.update(authenticated=True, pin_verified=True, csrf_token='test-csrf')
    monkeypatch.setattr(api.registry, 'get', lambda name: Mock() if name == 'data_manager' else None)
    monkeypatch.setattr(api, '_get_server_ssh_credentials', lambda server_id, manager: (
        {'id': server_id}, {'ip': '192.0.2.1', 'port': 22, 'user': 'admin', 'password': 'fixture-only'}))
    ssh = Mock()
    monkeypatch.setattr(paramiko, 'SSHClient', Mock(return_value=ssh))
    monkeypatch.setattr('app.routes.reset._load_known_hosts', Mock())
    connect = Mock()
    monkeypatch.setattr('app.routes.reset._connect', connect)
    client.ssh, client.connect = ssh, connect
    return client


def _reply(ssh, text):
    stdout = Mock()
    stdout.read.return_value = text.encode()
    ssh.exec_command.return_value = (Mock(), stdout, Mock())


def test_requires_login_and_csrf(client, history_client):
    assert history_client.post(URL, json={}, csrf=False).status_code == 403
    with client.session_transaction() as state:
        state.clear()
    assert client.post(URL, headers={'X-CSRF-Token': 'test-csrf'}).status_code == 401


def test_rewrites_only_history_script_on_strict_connection(history_client):
    _reply(history_client.ssh, 'OK\n')
    response = history_client.post(URL, headers={'X-CSRF-Token': 'test-csrf'})
    assert response.status_code == 200 and response.json['success'] is True
    policy = history_client.ssh.set_missing_host_key_policy.call_args.args[0]
    assert isinstance(policy, paramiko.RejectPolicy)
    command = history_client.ssh.exec_command.call_args.args[0]
    assert command.startswith('test -f /usr/local/bin/monitoring/update-metrics-history.sh')
    assert 'sudo -n tee /usr/local/bin/monitoring/update-metrics-history.sh' in command
    history_client.ssh.close.assert_called_once()


def test_failure_hides_details(history_client):
    _reply(history_client.ssh, 'sudo: a password is required')
    response = history_client.post(URL, headers={'X-CSRF-Token': 'test-csrf'})
    assert response.status_code == 502 and b'password is required' not in response.data
    history_client.connect.side_effect = RemoteConnectError('unknown_host')
    response = history_client.post(URL, headers={'X-CSRF-Token': 'test-csrf'})
    assert response.status_code == 502 and b'fixture-only' not in response.data
