"""Encrypted-only backups; restore to a new file before committing selection."""
import json
from pathlib import Path
import uuid

from .config_io import read_config, write_config
from .profile_transaction import profile_lock
from .vault_io import VaultConflict, VaultError, atomic_write, canonical


def validate(manager, raw):
    servers, dns = manager.split_payload(json.loads(manager.fernet.decrypt(raw).decode('utf-8')))
    sections = []
    for server in servers:
        for name, fields in (
            ('ssh_credentials', ('password', 'root_password', 'private_key', 'key_passphrase')),
            ('panel_credentials', ('user', 'password')),
            ('hoster_credentials', ('user', 'password')),
        ):
            section = server.get(name, {})
            if not isinstance(section, dict):
                raise VaultError('Invalid credentials in backup')
            sections.append((section, fields))
    for name in ('providers', 'domains', 'own_servers'):
        if name in dns and (not isinstance(dns[name], list) or
                            not all(isinstance(row, dict) for row in dns[name])):
            raise VaultError('Invalid DNS data in backup')
    sections.extend((provider, ('user', 'password')) for provider in dns.get('providers', []))
    for section, fields in sections:
        for field in fields:
            value = section.get(field)
            if value:
                if not isinstance(value, str):
                    raise VaultError('Invalid credential value in backup')
                if value.startswith('gAAAAA'):
                    manager.fernet.decrypt(value.encode()).decode('utf-8')
    return len(servers)


def _selection(manager, selected):
    config = read_config(Path(manager.app_data_dir) / 'config.json')
    if 'active_data_file' in config:
        saved = manager.get_active_data_path(config)
        if (canonical(saved) if saved else None) != (canonical(selected) if selected else None):
            raise VaultConflict('Active vault changed; reload before restoring')
    return config


def download(manager, selected):
    if not selected:
        raise VaultError('No active vault')
    with profile_lock(manager.app_data_dir):
        manager._check_profile_generation()
        _selection(manager, selected)
        raw = Path(selected).read_bytes()
        validate(manager, raw)
        return raw


def restore(manager, selected, raw):
    with profile_lock(manager.app_data_dir):
        manager._check_profile_generation()
        config = _selection(manager, selected)
        validate(manager, raw)  # No file is created until decryption/structure checks pass.
        target = Path(manager.app_data_dir) / 'data' / f'restored_{uuid.uuid4().hex}.enc'
        atomic_write(target, raw)
        config['active_data_file'] = str(target)
        # If commit fails, retain the new encrypted snapshot too: a post-replace
        # fsync error must never leave config pointing at a file we deleted.
        write_config(Path(manager.app_data_dir) / 'config.json', config)
        return str(target)
