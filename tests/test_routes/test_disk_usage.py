from unittest.mock import Mock
from .test_reset import reset_client
from app.routes import reset as routes
from app.services.disk_usage_payload import DISK_SOURCE


def test_disk_page_shows_commands(reset_client):
    response = reset_client.get('/servers/one/disk-usage')
    assert response.status_code == 200
    assert b'journalctl --disk-usage' in response.data
    assert b'sudo du -xhd1' in response.data


def test_disk_auth_and_csrf(client, reset_client):
    assert reset_client.post('/api/servers/one/disk-usage', json={}).status_code == 403


def test_disk_rejects_unauthenticated(client):
    assert client.post('/api/servers/one/disk-usage', json={}).status_code == 401


def test_disk_uses_only_fixed_payload(reset_client, monkeypatch):
    remote = Mock(return_value={'results': []})
    monkeypatch.setattr(routes, 'remote', remote)
    response = reset_client.post('/api/servers/one/disk-usage', json={'command': 'arbitrary-input'}, headers={'X-CSRF-Token': 'test-csrf'})
    assert response.status_code == 200
    assert remote.call_args.args[1] == []
    assert remote.call_args.kwargs['source'] == DISK_SOURCE


def test_disk_failure_hides_ssh_details(reset_client, monkeypatch):
    monkeypatch.setattr(routes, 'remote', Mock(side_effect=RuntimeError('private-detail')))
    response = reset_client.post('/api/servers/one/disk-usage', json={}, headers={'X-CSRF-Token': 'test-csrf'})
    assert response.status_code == 502
    assert b'private-detail' not in response.data
