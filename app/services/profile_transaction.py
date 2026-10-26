"""Recoverable profile commit. Private snapshots exist only until commit/rollback."""
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .vault_io import VaultError, atomic_write, file_lock

PENDING = '.key-rotation.pending'
GENERATION = '.profile-generation'


def generation(directory):
    try:
        return (Path(directory) / GENERATION).read_text(encoding='ascii').strip()
    except FileNotFoundError:
        return ''


@contextmanager
def profile_lock(directory, *, allow_pending=False):
    directory = Path(directory)
    with file_lock(directory / '.profile'):
        if not allow_pending and (directory / PENDING).exists():
            raise VaultError('Profile recovery is required. Restart the application before writing.')
        yield


def _sync_directory(path):
    if os.name != 'nt':
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _restore(directory, snapshot, name, exists):
    target = directory / name
    if exists:
        atomic_write(target, (snapshot / name).read_bytes())
    elif target.exists():
        target.unlink()
        _sync_directory(directory)


def _finish(directory, snapshot):
    # Remove the durable marker first: after this point all target files agree.
    (directory / PENDING).unlink()
    _sync_directory(directory)
    shutil.rmtree(snapshot)
    _sync_directory(directory)


def _recover_locked(directory):
    marker = directory / PENDING
    if not marker.exists():
        return False
    try:
        manifest = json.loads(marker.read_bytes())
        name = manifest['snapshot']
        if (not isinstance(name, str) or not name.startswith('.key-rotation-') or
                Path(name).name != name or manifest['state'] not in ('prepared', 'committed')):
            raise ValueError()
        snapshot = directory / name
        if snapshot.is_symlink() or not snapshot.is_dir():
            raise ValueError()
        if manifest['state'] == 'prepared':
            for name in ('.env', 'config.json', GENERATION):
                if not isinstance(manifest['existed'][name], bool):
                    raise ValueError()
                if manifest['existed'][name] and not (snapshot / name).is_file():
                    raise ValueError()
            for name in ('.env', 'config.json', GENERATION):
                _restore(directory, snapshot, name, manifest['existed'][name])
        _finish(directory, snapshot)
        return True
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise VaultError('Profile recovery is incomplete. Original snapshots were retained; writing is disabled.') from exc


def recover_profile(directory):
    """Called before dotenv loading; repeats rollback safely after another interruption."""
    directory = Path(directory)
    # No lock files or new directories on the ordinary startup path.
    if not (directory / PENDING).exists():
        return False
    with profile_lock(directory, allow_pending=True):
        return _recover_locked(directory)


def commit_profile(directory, env_bytes, config_bytes, new_generation):
    """Caller holds profile_lock; prepared -> rollback, committed -> keep new files."""
    directory = Path(directory)
    snapshot = Path(tempfile.mkdtemp(prefix='.key-rotation-', dir=directory))
    existed = {}
    marker = directory / PENDING
    try:
        for name in ('.env', 'config.json', GENERATION):
            source = directory / name
            existed[name] = source.exists()
            if existed[name]:
                atomic_write(snapshot / name, source.read_bytes())
        manifest = {'state': 'prepared', 'snapshot': snapshot.name, 'existed': existed}
        atomic_write(marker, json.dumps(manifest).encode())
        atomic_write(directory / '.env', env_bytes)
        atomic_write(directory / 'config.json', config_bytes)
        atomic_write(directory / GENERATION, new_generation.encode('ascii'))
        manifest['state'] = 'committed'
        atomic_write(marker, json.dumps(manifest).encode())
    except Exception:
        # BaseException deliberately escapes: power loss is handled at startup.
        if marker.exists():
            state = json.loads(marker.read_bytes()).get('state')
            if state == 'committed':
                # Durability is uncertain (e.g. directory fsync failed). Keep the
                # marker so all further writes are blocked until startup recovery.
                return
            _recover_locked(directory)
        else:
            shutil.rmtree(snapshot)
        raise
    # Cleanup failure after the commit must not switch runtime back to the old key.
    try:
        _finish(directory, snapshot)
    except OSError:
        pass
