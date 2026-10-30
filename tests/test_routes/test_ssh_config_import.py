import pytest

from app.services.ssh_config_import import read_local_ssh_config


@pytest.fixture
def authenticated(client):
    with client.session_transaction() as session:
        session.update(authenticated=True, pin_verified=True, csrf_token='test-csrf')
    return client


def test_import_route_requires_auth_and_pin(client):
    response = client.post('/ssh-config/import', json={}, headers={'X-CSRF-Token': 'bad'})
    assert response.status_code == 401
    with client.session_transaction() as session:
        session['authenticated'] = True
    assert client.post('/ssh-config/import', json={}, headers={'X-CSRF-Token': 'bad'}).status_code == 401


def test_import_route_requires_csrf(authenticated):
    response = authenticated.post('/ssh-config/import', json={}, headers={'X-CSRF-Token': 'bad'})
    assert response.status_code == 403


def test_import_is_explicit_and_returns_only_supported_fields(authenticated, tmp_path, monkeypatch):
    from unittest.mock import Mock

    ssh_dir = tmp_path / '.ssh'
    ssh_dir.mkdir()
    (ssh_dir / 'config').write_text('''
Host edge
  HostName 192.0.2.77
  User operator
  Port 2227
  IdentityFile ~/.ssh/id_ed25519
  ProxyJump secret-hop
  Password secret-password
# private-key-material must not be read
''')
    monkeypatch.setenv('HOME', str(tmp_path))

    reader = Mock(wraps=read_local_ssh_config)
    monkeypatch.setattr('app.services.ssh_config_import.read_local_ssh_config', reader)
    page = authenticated.get('/add_server')
    assert page.status_code == 200
    assert 'Import from ~/.ssh/config' in page.get_data(as_text=True)
    reader.assert_not_called()

    response = authenticated.post('/ssh-config/import', json={}, headers={'X-CSRF-Token': 'test-csrf'})
    reader.assert_called_once()
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    payload = response.get_json()
    assert payload['hosts'] == [{
        'alias': 'edge', 'host_name': '192.0.2.77', 'user': 'operator', 'port': 2227,
        'identity_file': str(ssh_dir / 'id_ed25519'), 'unsupported': ['line 7: ProxyJump', 'line 8: Password'],
    }]
    serialized = response.get_data(as_text=True)
    for private in ('secret-hop', 'secret-password', 'private-key-material'):
        assert private not in serialized


def test_import_route_reports_missing_file(authenticated, tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    response = authenticated.post('/ssh-config/import', json={}, headers={'X-CSRF-Token': 'test-csrf'})
    assert response.status_code == 404
    assert '~/.ssh/config' in response.get_json()['error']
