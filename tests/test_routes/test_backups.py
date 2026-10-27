import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from app.services import registry, backup_service
from app.services.data_manager_service import DataManagerService


@pytest.fixture
def inventory(app, client, tmp_path):
    manager = DataManagerService(Fernet.generate_key().decode(), str(tmp_path))
    path = tmp_path / 'data/original.enc'
    manager.save_servers([{'id': 1, 'name': 'Original', 'ssh_credentials': {
        'password': manager.encrypt_data('fixture-password')}}], str(path),
        dns={'domains': [{'id': 'demo', 'name': 'example.com', 'records': []}]})
    manager.update_user_config({'active_data_file': str(path)})
    registry.register('data_manager', manager)
    app.config['active_data_file'] = str(path)
    with client.session_transaction() as state:
        state.update(authenticated=True, pin_verified=True)
    return manager, path


def upload(client, raw, confirm='yes'):
    return client.post('/restore_backup', data={'backup_file': (io.BytesIO(raw), 'copy.enc'),
                                               'confirm_restore': confirm})


def test_download_is_encrypted_inventory_only(client, inventory):
    manager, path = inventory
    result = client.get('/download_backup')
    assert result.status_code == 200
    assert result.data == path.read_bytes()
    assert result.headers['Cache-Control'] == 'no-store'
    assert 'attachment' in result.headers['Content-Disposition']
    assert manager.secret_key.encode() not in result.data
    assert b'fixture-password' not in result.data
    rows, dns = manager.split_payload(json.loads(manager.fernet.decrypt(result.data)))
    assert rows[0]['name'] == 'Original' and dns['domains'][0]['name'] == 'example.com'


def test_restore_selects_new_file_preserving_original(app, client, inventory):
    manager, path = inventory
    raw = path.read_bytes()
    with patch('app.services.ssh_service.SSHService.close_all') as revoke:
        assert upload(client, raw).status_code == 302
        revoke.assert_called_once()
    target = Path(app.config['active_data_file'])
    assert target != path and target.read_bytes() == raw and path.read_bytes() == raw
    assert json.loads((Path(manager.app_data_dir) / 'config.json').read_text())['active_data_file'] == str(target)
    restarted = DataManagerService(manager.secret_key, manager.app_data_dir)
    assert restarted.load_servers(app.config)[0]['ssh_credentials']['password_decrypted'] == 'fixture-password'
    assert restarted.load_dns(app.config)['domains'][0]['name'] == 'example.com'
    assert target.stat().st_mode & 0o077 == 0


@pytest.mark.parametrize('case', ['broken', 'wrong-key', 'malformed', 'inner-key', 'dns'])
def test_invalid_restore_preserves_state(app, client, inventory, case):
    manager, path = inventory
    original = path.read_bytes()
    payload = [{'id': 1}]
    if case == 'inner-key':
        payload[0]['ssh_credentials'] = {'password': Fernet(Fernet.generate_key()).encrypt(b'fixture').decode()}
    if case == 'malformed': payload = {'servers': 'bad'}
    if case == 'dns': payload = {'servers': [], 'dns': {'domains': 'bad'}}
    raw = manager.fernet.encrypt(json.dumps(payload).encode())
    if case == 'broken': raw = b'broken'
    if case == 'wrong-key': raw = Fernet(Fernet.generate_key()).encrypt(b'[]')
    assert upload(client, raw).status_code == 302
    assert app.config['active_data_file'] == str(path)
    assert path.read_bytes() == original
    assert not list(path.parent.glob('restored_*'))


def test_failed_config_commit_keeps_old_selection(app, client, inventory):
    manager, path = inventory
    raw = path.read_bytes()
    with patch('app.services.backup_service.write_config', side_effect=OSError('fixture')):
        upload(client, raw)
    assert app.config['active_data_file'] == str(path)
    assert path.read_bytes() == raw
    config = json.loads((Path(manager.app_data_dir) / 'config.json').read_text())
    assert config['active_data_file'] == str(path)


def test_late_config_error_never_deletes_referenced_copy(app, client, inventory):
    manager, path = inventory
    from app.services.config_io import write_config
    def fail_after_commit(*args):
        write_config(*args)
        raise OSError('simulated fsync failure after replace')
    with patch('app.services.backup_service.write_config', side_effect=fail_after_commit):
        upload(client, path.read_bytes())
    config = json.loads((Path(manager.app_data_dir) / 'config.json').read_text())
    assert Path(config['active_data_file']).read_bytes() == path.read_bytes()
    assert path.exists()


def test_confirmation_and_csrf_required(app, client, inventory):
    _, path = inventory
    upload(client, path.read_bytes(), confirm='')
    assert app.config['active_data_file'] == str(path)
    assert client.post('/restore_backup', csrf=False).status_code == 403


@pytest.mark.parametrize('authenticated,pin', [(False, False), (True, False)])
def test_backup_requires_auth_and_pin(client, inventory, authenticated, pin):
    with client.session_transaction() as state:
        state['authenticated'], state['pin_verified'] = authenticated, pin
    assert client.get('/download_backup').status_code in (302, 401)
    assert upload(client, inventory[1].read_bytes()).status_code in (302, 401)


def test_stale_selection_is_rejected(app, client, inventory):
    manager, path = inventory
    manager.update_user_config({'active_data_file': None})
    upload(client, path.read_bytes())
    assert not list(path.parent.glob('restored_*'))
