"""Synthetic SSH clients, generated public keys and temporary profiles only."""
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

import paramiko
import pytest
from cryptography.fernet import Fernet

from app.services.ssh_service import SSHService, SSHSessionInvalidated
from app.services.ssh_trust import UnknownHostKeyError, KnownHostsError, host_key_message
from app.services.ssh_auth import fingerprint
from app.services.data_manager_service import DataManagerService


@pytest.fixture
def pool(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    for name in ('_connection_pool', '_connection_signatures', '_connection_locks', '_host_epochs'):
        monkeypatch.setattr(SSHService, name, {})
    monkeypatch.setattr(SSHService, '_live_clients', weakref.WeakKeyDictionary())
    monkeypatch.setattr(SSHService, '_last_trust_revision', None)
    monkeypatch.setattr(SSHService, '_pool_epoch', 0)
    clients = []
    def create():
        client = Mock()
        client.exec_command.return_value = (Mock(), Mock(), Mock())
        clients.append(client)
        return client
    monkeypatch.setattr(paramiko, 'SSHClient', create)
    monkeypatch.setattr('app.services.ssh_service.connect_kwargs', lambda *a, **k: {})
    yield clients
    SSHService.close_all()


def get(password='fixture', **kwargs):
    return SSHService.get_connection_pooled('192.0.2.10', 2222, 'operator', password, **kwargs)


def test_unchanged_credentials_reuse_transport(pool):
    first = get()
    assert get() is first
    assert len(pool) == 1
    first.close.assert_not_called()


def test_changed_password_closes_old_transport(pool):
    first = get('old-password')
    second = get('new-password')
    assert second is not first
    first.close.assert_called_once()
    assert all(b'password' not in value for value in SSHService._connection_signatures.values())


def test_replaced_private_key_at_same_path_is_not_reused(pool, tmp_path):
    path = tmp_path / 'key'
    path.write_text('first synthetic key')
    first = get(key=str(path))
    path.write_text('other synthetic key')
    assert get(key=str(path)) is not first
    first.close.assert_called_once()


def test_unreadable_private_key_revokes_old_session(pool, tmp_path):
    path = tmp_path / 'key'
    path.write_text('synthetic')
    first = get(key=str(path))
    path.unlink()
    with pytest.raises(paramiko.AuthenticationException):
        get(key=str(path))
    first.close.assert_called_once()
    assert not SSHService._connection_pool


def test_known_hosts_change_revokes_pool_and_dedicated_clients(pool, tmp_path):
    first = get()
    other = SSHService.get_connection_pooled('192.0.2.11', 22, 'root', 'fixture')
    dedicated = Mock()
    SSHService.connect_managed(dedicated, hostname='192.0.2.12')
    directory = tmp_path / '.ssh'
    directory.mkdir()
    (directory / 'known_hosts').write_text('# changed trust store\n')
    assert get() is not first
    first.close.assert_called_once()
    other.close.assert_called_once()
    dedicated.close.assert_called_once()


def test_invalidation_fences_handshake_in_progress(pool, monkeypatch):
    started, resume = threading.Event(), threading.Event()
    client = Mock()
    def connect(*args, **kwargs):
        started.set()
        assert resume.wait(5)
    client.connect.side_effect = connect
    monkeypatch.setattr(paramiko, 'SSHClient', lambda: client)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(get)
        assert started.wait(5)
        SSHService.invalidate_hosts({'192.0.2.10'})
        resume.set()
        with pytest.raises(SSHSessionInvalidated):
            future.result(timeout=5)
    assert not SSHService._connection_pool
    client.close.assert_called_once()


@pytest.mark.parametrize('change', ['password', 'user', 'port', 'address', 'remove'])
def test_saved_card_changes_revoke_sessions(pool, tmp_path, change):
    manager = DataManagerService(Fernet.generate_key().decode(), str(tmp_path))
    path = str(tmp_path / 'inventory.enc')
    manager.save_servers([{'id': 1, 'ip_address': '192.0.2.10', 'ssh_credentials': {
        'user': 'operator', 'port': 2222, 'password': 'encrypted-fixture'}}], path)
    first = get()
    rows = manager.load_servers({'active_data_file': path})
    if change == 'remove':
        rows.clear()
    elif change == 'address':
        rows[0]['ip_address'] = '192.0.2.20'
    else:
        rows[0]['ssh_credentials'][change] = 22 if change == 'port' else 'updated'
    manager.save_servers(rows, path)
    first.close.assert_called_once()


def test_failed_save_does_not_revoke(pool, tmp_path):
    manager = DataManagerService(Fernet.generate_key().decode(), str(tmp_path))
    path = str(tmp_path / 'inventory.enc')
    manager.save_servers([{'id': 1, 'ip_address': '192.0.2.10'}], path)
    first = get()
    rows = manager.load_servers({'active_data_file': path})
    rows.clear()
    with patch('app.services.vault_io.os.replace', side_effect=OSError('fixture')):
        with pytest.raises(OSError):
            manager.save_servers(rows, path)
    first.close.assert_not_called()


def test_diagnostics_show_only_endpoint_and_public_fingerprints(app):
    from app.routes.api import _ssh_failure_message
    old, new = paramiko.RSAKey.generate(1024), paramiko.RSAKey.generate(1024)
    for error in (UnknownHostKeyError('[192.0.2.10]:2222', new),
                  paramiko.BadHostKeyException('[192.0.2.10]:2222', new, old)):
        text = _ssh_failure_message(error)
        assert '[192.0.2.10]:2222' in text
        assert fingerprint(new) in text
        assert new.get_base64() not in text
        assert 'ssh-keygen -R' not in text
    assert fingerprint(old) in _ssh_failure_message(error)
    assert host_key_message(KnownHostsError('CANARY-private-line'))
    assert 'CANARY' not in host_key_message(KnownHostsError('CANARY-private-line'))


def test_same_secret_reencrypted_on_non_ssh_edit_keeps_connection(pool, tmp_path):
    manager = DataManagerService(Fernet.generate_key().decode(), str(tmp_path))
    path = str(tmp_path / 'inventory.enc')
    manager.save_servers([{'id': 1, 'ip_address': '192.0.2.10', 'ssh_credentials': {
        'user': 'operator', 'port': 2222, 'password': manager.encrypt_data('fixture')}}], path)
    first = get()
    rows = manager.load_servers({'active_data_file': path})
    rows[0]['name'] = 'new title'
    rows[0]['ssh_credentials']['password'] = manager.encrypt_data('fixture')
    manager.save_servers(rows, path)
    first.close.assert_not_called()


def test_dedicated_connection_is_closed_when_card_is_revoked(pool):
    client = Mock()
    SSHService.connect_managed(client, hostname='192.0.2.10', username='operator')
    SSHService.invalidate_hosts({'192.0.2.10'})
    client.close.assert_called_once()


def test_unknown_host_hint_survives_connection_wrapper(app):
    from app.routes.api import _ssh_failure_message
    key = paramiko.RSAKey.generate(1024)
    try:
        try:
            raise UnknownHostKeyError('[192.0.2.10]:2222', key)
        except Exception:
            raise RuntimeError('CANARY: should not appear')
    except Exception as error:
        text = _ssh_failure_message(error)
    assert fingerprint(key) in text
    assert 'CANARY' not in text


def test_trust_changed_after_loading_aborts_before_credentials(pool, tmp_path):
    from app.services.ssh_trust import load_known_hosts
    client = Mock()
    load_known_hosts(client)
    directory = tmp_path / '.ssh'
    directory.mkdir()
    (directory / 'known_hosts').write_text('# new trust revision\n')
    with pytest.raises(SSHSessionInvalidated):
        SSHService.connect_managed(client, hostname='192.0.2.10', password='CANARY')
    client.connect.assert_not_called()


def test_dedicated_changed_host_diagnostic_keeps_nonstandard_port(pool):
    client = Mock()
    client.connect.side_effect = paramiko.BadHostKeyException('192.0.2.10', None, None)
    with pytest.raises(paramiko.BadHostKeyException) as caught:
        SSHService.connect_managed(client, hostname='192.0.2.10', port=2222)
    assert caught.value.hostname == '[192.0.2.10]:2222'


@pytest.mark.parametrize('line', ['broken-entry', '@revoked example.com ssh-ed25519 invalid'])
def test_malformed_trust_is_rejected_before_connect(pool, tmp_path, line):
    from app.services.ssh_trust import load_known_hosts
    directory = tmp_path / '.ssh'
    directory.mkdir()
    (directory / 'known_hosts').write_text(line + '\n')
    client = Mock()
    with pytest.raises(KnownHostsError):
        load_known_hosts(client)
    client.connect.assert_not_called()
    client.load_system_host_keys.assert_not_called()
