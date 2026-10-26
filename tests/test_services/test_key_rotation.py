import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet, InvalidToken
from dotenv import dotenv_values

from app.services.config_io import read_config, write_config
from app.services.data_manager_service import DataManagerService
from app.services.key_rotation import rotate_key
from app.services import profile_transaction as transaction
from app.services.vault_io import VaultConflict, VaultError
from tools.check_public_files import is_private


class PowerLoss(BaseException):
    pass


@pytest.fixture
def profile(tmp_path):
    key = Fernet.generate_key().decode()
    manager = DataManagerService(key, str(tmp_path))
    path = tmp_path / 'data' / 'original.enc'
    manager.save_servers([{'id': 1, 'name': 'fixture', 'ssh_credentials': {
        'password': manager.encrypt_data(' CANARY-secret '), 'private_key': manager.encrypt_data('fixture-key')}}],
        str(path), dns={'providers': [{'id': 'provider', 'password': manager.encrypt_data('dns-secret')}]})
    config = read_config(tmp_path / 'config.json')
    config.update(active_data_file=str(path), ui={'zoom': '100'}, secret_pin={'current_pin': '5678'})
    write_config(tmp_path / 'config.json', config)
    (tmp_path / '.env').write_text('# fixture\nexport SECRET_KEY = "' + key + '"\nOTHER_SETTING=preserved\n')
    return manager, path, tmp_path


def assert_profile_readable(directory, expected_key):
    assert dotenv_values(directory / '.env')['SECRET_KEY'] == expected_key
    config = read_config(directory / 'config.json')
    assert config['ui'] == {'zoom': '100'}
    assert config['secret_pin']['current_pin'] == '5678'
    manager = DataManagerService(expected_key, str(directory))
    rows, dns = manager.read_payload(config['active_data_file'])
    assert manager.decrypt_data(rows[0]['ssh_credentials']['password']) == ' CANARY-secret '
    assert manager.decrypt_data(rows[0]['ssh_credentials']['private_key']) == 'fixture-key'
    assert manager.decrypt_data(dns['providers'][0]['password']) == 'dns-secret'
    assert dotenv_values(directory / '.env')['OTHER_SETTING'] == 'preserved'


def test_rotation_preserves_data_and_fences_stale_managers(profile):
    manager, path, directory = profile
    raw = path.read_bytes()
    stale = manager.load_servers({'active_data_file': str(path)})
    second_process = DataManagerService(manager.secret_key, str(directory))
    key = Fernet.generate_key().decode()
    replacement, target = rotate_key(manager, str(path), key)
    assert_profile_readable(directory, key)
    assert path.read_bytes() == raw
    assert target != str(path)
    assert replacement.secret_key == key
    assert not (directory / transaction.PENDING).exists()
    assert not list(directory.glob('.key-rotation-*'))
    for old in (manager, second_process):
        with pytest.raises(VaultConflict):
            old.save_servers(stale, str(path))
        with pytest.raises(VaultConflict):
            old.read_payload(str(path))
    if os.name != 'nt':
        assert (directory / '.env').stat().st_mode & 0o777 == 0o600


def crash_after(monkeypatch, directory, stage, exception):
    write = transaction.atomic_write
    fired = False
    def interrupted(path, content):
        nonlocal fired
        write(path, content)
        path = Path(path)
        current = json.loads(content)['state'] if path.name == transaction.PENDING else path.name
        if path.parent == directory and current == stage and not fired:
            fired = True
            raise exception()
    monkeypatch.setattr(transaction, 'atomic_write', interrupted)


@pytest.mark.parametrize('stage', ['prepared', '.env', 'config.json', transaction.GENERATION, 'committed'])
def test_power_loss_recovers_one_complete_generation(profile, monkeypatch, stage):
    manager, path, directory = profile
    new_key = Fernet.generate_key().decode()
    crash_after(monkeypatch, directory, stage, PowerLoss)
    with pytest.raises(PowerLoss):
        rotate_key(manager, str(path), new_key)
    assert (directory / transaction.PENDING).exists()
    # No writes from a still-running old request while recovery is pending.
    with pytest.raises(VaultError):
        manager.save_servers([], str(path))
    assert transaction.recover_profile(directory) is True
    assert transaction.recover_profile(directory) is False
    assert_profile_readable(directory, new_key if stage == 'committed' else manager.secret_key)


@pytest.mark.parametrize('stage', ['.env', 'config.json', transaction.GENERATION])
def test_io_error_rolls_back_before_returning(profile, monkeypatch, stage):
    manager, path, directory = profile
    crash_after(monkeypatch, directory, stage, OSError)
    with pytest.raises(OSError):
        rotate_key(manager, str(path), Fernet.generate_key().decode())
    assert_profile_readable(directory, manager.secret_key)
    assert not (directory / transaction.PENDING).exists()


def test_committed_marker_fsync_error_keeps_runtime_and_disk_consistent(profile, monkeypatch):
    manager, path, directory = profile
    key = Fernet.generate_key().decode()
    crash_after(monkeypatch, directory, 'committed', OSError)
    replacement, _ = rotate_key(manager, str(path), key)
    assert replacement.secret_key == key
    assert (directory / transaction.PENDING).exists()
    with pytest.raises(VaultError):
        replacement.read_payload(str(path))
    transaction.recover_profile(directory)
    assert_profile_readable(directory, key)


def test_interrupted_rollback_can_itself_be_recovered(profile, monkeypatch):
    manager, path, directory = profile
    crash_after(monkeypatch, directory, 'config.json', PowerLoss)
    with pytest.raises(PowerLoss):
        rotate_key(manager, str(path), Fernet.generate_key().decode())
    restore = transaction._restore
    def interrupted(*args):
        restore(*args)
        raise PowerLoss()
    with patch.object(transaction, '_restore', interrupted):
        with pytest.raises(PowerLoss):
            transaction.recover_profile(directory)
    assert transaction.recover_profile(directory)
    assert_profile_readable(directory, manager.secret_key)


def test_missing_active_file_is_not_an_empty_rotation(profile):
    manager, path, directory = profile
    path.unlink()
    before = (directory / '.env').read_bytes()
    with pytest.raises(FileNotFoundError):
        rotate_key(manager, str(path), Fernet.generate_key().decode())
    assert (directory / '.env').read_bytes() == before
    assert not list(directory.glob('.key-rotation-*'))


def test_corrupt_inner_secret_aborts_without_switching(profile):
    manager, path, directory = profile
    rows, dns = manager.read_payload(str(path))
    rows[0]['ssh_credentials']['password'] = 'gAAAAA-invalid-secret'
    manager.save_servers(rows, str(path), dns=dns)
    before = (directory / '.env').read_bytes()
    with pytest.raises(InvalidToken):
        rotate_key(manager, str(path), Fernet.generate_key().decode())
    assert (directory / '.env').read_bytes() == before


def test_different_configured_key_requires_restart(profile):
    manager, path, directory = profile
    (directory / '.env').write_text('SECRET_KEY=' + Fernet.generate_key().decode() + '\n')
    with pytest.raises(VaultConflict):
        rotate_key(manager, str(path), Fernet.generate_key().decode())


def test_recovery_snapshots_are_private():
    for path in ('.key-rotation.pending', '.key-rotation-abcd/config.json',
                 'docs/.key-rotation-abcd/.env', '.profile-generation'):
        assert is_private(path)


def test_app_factory_recovers_before_registering_old_key(profile, monkeypatch):
    import app as app_module
    from app.config import TestingConfig
    from app.services import registry
    manager, path, directory = profile
    new_key = Fernet.generate_key().decode()
    crash_after(monkeypatch, directory, 'config.json', PowerLoss)
    with pytest.raises(PowerLoss):
        rotate_key(manager, str(path), new_key)

    class RecoveryConfig(TestingConfig):
        APP_DATA_DIR = str(directory)
        DATA_DIR = str(directory / 'data')
        UPLOAD_FOLDER = str(directory / 'uploads')
        SECRET_KEY = new_key  # Simulates a key loaded before the interrupted rollback.
        LOG_FILE = str(directory / 'test.log')

    monkeypatch.setitem(app_module.config_by_name, 'recovery_test', RecoveryConfig)
    restarted = app_module.create_app('recovery_test')
    assert restarted.config['SECRET_KEY'] == manager.secret_key
    assert restarted.config['active_data_file'] == str(path)
    assert registry.get('data_manager').secret_key == manager.secret_key
    assert_profile_readable(directory, manager.secret_key)


def test_factory_uses_committed_key_instead_of_stale_class_config(profile, monkeypatch):
    import app as app_module
    from app.config import TestingConfig
    from app.services import registry
    manager, path, directory = profile
    key = Fernet.generate_key().decode()
    _, target = rotate_key(manager, str(path), key)

    class CommittedConfig(TestingConfig):
        APP_DATA_DIR = str(directory)
        DATA_DIR = str(directory / 'data')
        UPLOAD_FOLDER = str(directory / 'uploads')
        SECRET_KEY = manager.secret_key
        LOG_FILE = str(directory / 'test.log')

    monkeypatch.setitem(app_module.config_by_name, 'committed_test', CommittedConfig)
    restarted = app_module.create_app('committed_test')
    assert restarted.config['SECRET_KEY'] == key
    assert restarted.config['active_data_file'] == target
    assert registry.get('data_manager').secret_key == key


def test_damaged_recovery_manifest_blocks_writes(profile):
    manager, path, directory = profile
    original = (directory / '.env').read_bytes()
    (directory / transaction.PENDING).write_text('{broken')
    with pytest.raises(VaultError):
        transaction.recover_profile(directory)
    with pytest.raises(VaultError):
        manager.save_servers([], str(path))
    assert (directory / '.env').read_bytes() == original


def test_ordinary_config_writer_cannot_overwrite_rotation(profile):
    manager, path, directory = profile
    stale = read_config(directory / 'config.json')
    key = Fernet.generate_key().decode()
    rotate_key(manager, str(path), key)
    stale['ui']['zoom'] = '60'
    with pytest.raises(VaultConflict):
        write_config(directory / 'config.json', stale)
    assert_profile_readable(directory, key)


def _crash_worker(directory, key, active_file, new_key):
    manager = DataManagerService(key, directory)
    write = transaction.atomic_write
    def interrupted(path, content):
        write(path, content)
        if Path(path) == Path(directory) / 'config.json':
            os._exit(86)  # Real abrupt termination: no finally blocks or rollback.
    transaction.atomic_write = interrupted
    rotate_key(manager, active_file, new_key)


def test_process_termination_releases_lock_and_startup_can_recover(profile):
    import multiprocessing
    manager, path, directory = profile
    context = multiprocessing.get_context('spawn')
    worker = context.Process(target=_crash_worker, args=(str(directory), manager.secret_key, str(path),
                                                       Fernet.generate_key().decode()))
    worker.start()
    try:
        worker.join(timeout=15)
        assert worker.exitcode == 86
        assert transaction.recover_profile(directory)
        assert_profile_readable(directory, manager.secret_key)
    finally:
        if worker.is_alive():
            worker.terminate()
            worker.join()
