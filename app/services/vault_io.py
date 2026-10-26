"""Атомарные записи и межпроцессная блокировка локального хранилища."""
import hashlib
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path


class VaultError(ValueError):
    """Безопасное сообщение: содержимое хранилища не включается в ошибку."""


class VaultConflict(VaultError):
    pass


class ServersSnapshot(list):
    def __init__(self, values, path, revision):
        super().__init__(values)
        self.vault_path = path
        self.vault_revision = revision


_locks_guard = threading.Lock()
_locks = {}
_held = threading.local()


def canonical(path):
    return os.path.realpath(os.path.abspath(path))


def revision(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


@contextmanager
def file_lock(path):
    """Sidecar не заменяется вместе с данными, поэтому блокировка стабильна."""
    path = canonical(path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with _locks_guard:
        lock = _locks.setdefault(path, threading.RLock())
    with lock:
        held = getattr(_held, 'paths', None)
        if held is None:
            held = _held.paths = set()
        if path in held:
            yield
            return
        fd = os.open(path + '.lock', os.O_CREAT | os.O_RDWR, 0o600)
        try:
            if os.name == 'nt':
                import msvcrt
                if os.fstat(fd).st_size == 0:
                    os.write(fd, b'0')
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX)
            held.add(path)
            yield
        finally:
            held.discard(path)
            # Закрытие fd освобождает блокировку и при исключении.
            os.close(fd)


def atomic_write(path, data):
    """Тот же filesystem, 0600, fsync до replace; оригинал цел до replace."""
    path = canonical(path)
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.vault-', dir=parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        if os.name != 'nt':
            directory = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


class DnsSnapshot(dict):
    def __init__(self, values, path, revision):
        super().__init__(values)
        self.vault_path = path
        self.vault_revision = revision
