"""Атомарная запись профиля с проверкой версии прочитанного файла."""
import json
from .vault_io import atomic_write, canonical, file_lock, revision, VaultError, VaultConflict


class ConfigSnapshot(dict):
    def __init__(self, values, path, raw):
        super().__init__(values)
        self.path = canonical(path)
        self.revision = revision(raw)


def read_config(path):
    try:
        with open(path, 'rb') as stream:
            raw = stream.read()
    except FileNotFoundError:
        raw = None
    try:
        data = json.loads(raw) if raw is not None else {}
        if not isinstance(data, dict):
            raise ValueError()
    except (ValueError, UnicodeError) as exc:
        raise VaultError('Configuration is unreadable; writing is disabled.') from exc
    return ConfigSnapshot(data, path, raw)


def write_config(path, data):
    path = canonical(path)
    if not isinstance(data, ConfigSnapshot) or data.path != path:
        raise VaultConflict('Read configuration before changing it.')
    with file_lock(path):
        current = read_config(path)
        if current.revision != data.revision:
            raise VaultConflict('Configuration changed; reload and retry.')
        raw = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode()
        atomic_write(path, raw)
        data.revision = revision(raw)
    return True
