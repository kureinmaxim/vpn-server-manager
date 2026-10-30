"""External vault import commits encrypted data and selection under one profile lock."""
import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.services import external_import
from app.services.data_manager_service import DataManagerService
from app.services.config_io import read_config, write_config
from app.services.vault_io import VaultConflict


def profile(tmp_path):
    manager = DataManagerService(Fernet.generate_key().decode(), str(tmp_path))
    current = tmp_path / 'data' / 'servers.enc'
    manager.save_servers([{
        'id': 1, 'name': 'current', 'ip_address': '192.0.2.1',
        'ssh_credentials': {'password': manager.encrypt_data('current-password')},
    }], str(current))
    config_path = tmp_path / 'config.json'
    config = {'active_data_file': str(current), 'keep': 'setting'}
    snapshot = read_config(config_path)
    snapshot.update(config)
    write_config(config_path, snapshot)
    return manager, current, config


def external_file(tmp_path, manager, rows):
    source = DataManagerService(Fernet.generate_key().decode(), str(tmp_path / 'foreign'))
    path = tmp_path / 'foreign.enc'
    source.save_servers(rows(source), str(path))
    return source, path.read_bytes()


def test_external_import_reencrypts_secrets_and_commits_selection(tmp_path):
    manager, current, runtime = profile(tmp_path)
    source, raw = external_file(tmp_path, manager, lambda foreign: [{
        'id': 99, 'name': 'imported', 'ip_address': '192.0.2.2',
        'ssh_credentials': {'password': foreign.encrypt_data('imported-password')},
    }])

    result = external_import.merge_external_vault(manager, runtime, raw, source.secret_key)

    assert result['added_count'] == 1 and result['skipped_count'] == 0
    assert result['active_data_file'] != str(current)
    assert runtime['active_data_file'] == str(current)  # Service does not mutate runtime state.
    stored_config = read_config(tmp_path / 'config.json')
    assert stored_config['active_data_file'] == result['active_data_file']
    assert stored_config['keep'] == 'setting'
    servers = manager.load_servers(stored_config)
    imported = next(row for row in servers if row['name'] == 'imported')
    assert manager.decrypt_data(imported['ssh_credentials']['password']) == 'imported-password'


def test_external_import_rejects_inner_secret_with_wrong_key_without_switching(tmp_path):
    manager, current, runtime = profile(tmp_path)
    source, raw = external_file(tmp_path, manager, lambda _foreign: [{
        'id': 99, 'name': 'bad', 'ip_address': '192.0.2.2',
        'ssh_credentials': {'password': 'gAAAAA-invalid-inner-token'},
    }])

    with pytest.raises(InvalidToken):
        external_import.merge_external_vault(manager, runtime, raw, source.secret_key)

    assert read_config(tmp_path / 'config.json')['active_data_file'] == str(current)
    assert manager.load_servers(runtime)[0]['name'] == 'current'


def test_external_import_detects_runtime_selection_conflict(tmp_path):
    manager, current, runtime = profile(tmp_path)
    source, raw = external_file(tmp_path, manager, lambda _foreign: [{'name': 'new'}])
    stale_runtime = dict(runtime, active_data_file=str(tmp_path / 'data' / 'different.enc'))

    with pytest.raises(VaultConflict):
        external_import.merge_external_vault(manager, stale_runtime, raw, source.secret_key)

    assert read_config(tmp_path / 'config.json')['active_data_file'] == str(current)


def test_external_import_config_write_failure_never_switches_active_vault(tmp_path, monkeypatch):
    manager, current, runtime = profile(tmp_path)
    source, raw = external_file(tmp_path, manager, lambda foreign: [{
        'id': 99, 'name': 'new', 'ip_address': '192.0.2.3',
        'ssh_credentials': {'password': foreign.encrypt_data('new-password')},
    }])
    monkeypatch.setattr(external_import, 'write_config',
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError('disk full')))

    with pytest.raises(OSError):
        external_import.merge_external_vault(manager, runtime, raw, source.secret_key)

    assert read_config(tmp_path / 'config.json')['active_data_file'] == str(current)
    assert runtime['active_data_file'] == str(current)
    assert manager.load_servers(runtime)[0]['name'] == 'current'
    assert list((tmp_path / 'data').glob('merged_*.enc'))


def test_external_import_follows_config_if_replace_succeeded_before_error(tmp_path, monkeypatch):
    manager, current, runtime = profile(tmp_path)
    source, raw = external_file(tmp_path, manager, lambda foreign: [{
        'id': 99, 'name': 'new', 'ip_address': '192.0.2.4',
        'ssh_credentials': {'password': foreign.encrypt_data('new-password')},
    }])
    real_write_config = external_import.write_config

    def write_then_raise(path, config):
        real_write_config(path, config)
        raise OSError('directory fsync failed after replace')

    monkeypatch.setattr(external_import, 'write_config', write_then_raise)

    result = external_import.merge_external_vault(manager, runtime, raw, source.secret_key)

    assert result['active_data_file'] != str(current)
    assert read_config(tmp_path / 'config.json')['active_data_file'] == result['active_data_file']
    assert runtime['active_data_file'] == str(current)  # Route applies the returned selection after commit.
