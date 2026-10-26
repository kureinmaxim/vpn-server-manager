import os
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from app.services.data_manager_service import DataManagerService
from app.services.vault_io import VaultError, VaultConflict


@pytest.fixture
def vault(tmp_path):
    manager = DataManagerService(Fernet.generate_key().decode(), str(tmp_path))
    path = str(tmp_path / 'inventory.enc')
    manager.save_servers([{'id': 1, 'name': 'original'}], path)
    return manager, path, {'active_data_file': path}


@pytest.mark.parametrize('raw', [b'', b'broken', Fernet(Fernet.generate_key()).encrypt(b'[]')])
def test_corruption_never_reads_as_empty_or_allows_overwrite(vault, raw):
    manager, path, config = vault
    Path(path).write_bytes(raw)
    with pytest.raises(VaultError):
        manager.load_servers(config)
    with pytest.raises(VaultError):
        manager.save_servers([], path)
    assert Path(path).read_bytes() == raw


def test_stale_snapshot_is_rejected(vault):
    manager, path, config = vault
    first = manager.load_servers(config)
    second = manager.load_servers(config)
    first[0]['name'] = 'first'
    manager.save_servers(first, path)
    second[0]['name'] = 'second'
    with pytest.raises(VaultConflict):
        manager.save_servers(second, path)
    assert manager.load_servers(config)[0]['name'] == 'first'


def test_second_manager_cannot_overwrite_a_stale_snapshot(vault, tmp_path):
    manager, path, config = vault
    other = DataManagerService(manager.secret_key, str(tmp_path))
    first, second = manager.load_servers(config), other.load_servers(config)
    manager.save_servers(first, path)
    with pytest.raises(VaultConflict):
        other.save_servers(second, path)


def test_failed_replace_preserves_old_vault(vault):
    manager, path, config = vault
    raw = Path(path).read_bytes()
    with patch('app.services.vault_io.os.replace', side_effect=OSError('disk failure')):
        with pytest.raises(OSError):
            manager.save_servers(manager.load_servers(config), path)
    assert Path(path).read_bytes() == raw
    assert not list(Path(path).parent.glob('.vault-*'))


def test_backup_is_previous_encrypted_snapshot(vault):
    manager, path, config = vault
    old = Path(path).read_bytes()
    rows = manager.load_servers(config)
    rows[0]['name'] = 'updated'
    manager.save_servers(rows, path)
    assert Path(path + '.backup.enc').read_bytes() == old
    assert b'original' not in old
    if os.name != 'nt':
        assert Path(path).stat().st_mode & 0o777 == 0o600


def test_deleted_file_is_not_silently_recreated(vault):
    manager, path, config = vault
    rows = manager.load_servers(config)
    Path(path).unlink()
    with pytest.raises(VaultConflict):
        manager.save_servers(rows, path)


def test_stale_dns_cannot_overwrite_server_update(vault):
    manager, path, config = vault
    dns = manager.load_dns(config)
    rows = manager.load_servers(config)
    rows[0]['name'] = 'updated'
    manager.save_servers(rows, path)
    with pytest.raises(VaultConflict):
        manager.save_dns(dns, path)


def _writer(key, path, name, barrier, queue):
    manager = DataManagerService(key, str(Path(path).parent))
    rows = manager.load_servers({'active_data_file': path})
    rows[0]['name'] = name
    barrier.wait(timeout=15)
    try:
        manager.save_servers(rows, path)
        queue.put('saved')
    except VaultConflict:
        queue.put('conflict')


def test_process_writers_serialize_and_detect_conflict(vault):
    import multiprocessing
    manager, path, config = vault
    context = multiprocessing.get_context('spawn')
    barrier, queue = context.Barrier(2), context.Queue()
    workers = [context.Process(target=_writer, args=(manager.secret_key, path, name, barrier, queue))
               for name in ('first', 'second')]
    try:
        for worker in workers:
            worker.start()
        assert sorted(queue.get(timeout=20) for _ in workers) == ['conflict', 'saved']
        for worker in workers:
            worker.join(timeout=5)
            assert worker.exitcode == 0
        assert manager.load_servers(config)[0]['name'] in ('first', 'second')
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join()


def test_backup_can_be_recovered_to_new_file_without_touching_corruption(vault, tmp_path):
    manager, path, config = vault
    rows = manager.load_servers(config)
    rows[0]['name'] = 'new'
    manager.save_servers(rows, path)
    Path(path).write_bytes(b'broken')
    old, dns = manager.read_payload(path + '.backup.enc')
    recovery = str(tmp_path / 'recovered.enc')
    manager.save_servers(old, recovery, dns=dns)
    assert manager.load_servers({'active_data_file': recovery})[0]['name'] == 'original'
    assert Path(path).read_bytes() == b'broken'


@pytest.mark.parametrize('payload', [{'servers': [], 'dns': 'invalid'}, [None]])
def test_invalid_payload_is_not_treated_as_empty(vault, payload):
    import json
    manager, path, config = vault
    raw = manager.fernet.encrypt(json.dumps(payload).encode())
    Path(path).write_bytes(raw)
    with pytest.raises(VaultError):
        manager.load_servers(config)
    with pytest.raises(VaultError):
        manager.save_servers([], path)
    assert Path(path).read_bytes() == raw


def test_failed_final_replace_leaves_old_data_and_recoverable_backup(vault):
    manager, path, config = vault
    raw = Path(path).read_bytes()
    replace = os.replace
    def fail_final(source, target):
        if str(target) == str(Path(path).resolve()):
            raise OSError('simulated final replace failure')
        return replace(source, target)
    with patch('app.services.vault_io.os.replace', side_effect=fail_final):
        with pytest.raises(OSError):
            manager.save_servers(manager.load_servers(config), path)
    assert Path(path).read_bytes() == raw
    assert Path(path + '.backup.enc').read_bytes() == raw
