"""Merge an external encrypted vault and switch selection as one profile write."""
import json
import uuid
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from .config_io import read_config, write_config
from . import dns_registry
from .profile_transaction import profile_lock
from .vault_io import VaultConflict, VaultError, canonical


class CurrentVaultUnreadable(VaultError):
    """The selected local vault could not be decrypted with the running key."""


def _same_path(left, right):
    return (canonical(left) if left else None) == (canonical(right) if right else None)


def _reencrypt_secret(value, external_fernet, manager):
    if not value:
        return value
    if not isinstance(value, str):
        raise VaultError('Invalid external credential value')
    if value.startswith('gAAAAA'):
        # A Fernet-looking inner secret must match the same external key as the vault.
        plain = external_fernet.decrypt(value.encode()).decode('utf-8')
    else:
        # Legacy plaintext credential fields are migrated into the local encrypted vault.
        plain = value
    return manager.encrypt_data(plain)


def _reencrypt_server_secrets(servers, start, external_fernet, manager):
    fields = {
        'ssh_credentials': ('password', 'root_password', 'private_key', 'key_passphrase'),
        'panel_credentials': ('user', 'password'),
        'hoster_credentials': ('user', 'password'),
    }
    for server in servers[start:]:
        for section_name, secret_names in fields.items():
            section = server.get(section_name)
            if section is None:
                continue
            if not isinstance(section, dict):
                raise VaultError('Invalid external credentials section')
            for field in secret_names:
                value = section.get(field)
                if value:
                    section[field] = _reencrypt_secret(value, external_fernet, manager)


def merge_external_vault(manager, runtime_config, encrypted_data, external_key):
    """Validate, merge and persist imported data before returning a new selection.

    The profile lock covers selection checks, current-vault reads, merge, new vault
    creation, and config switch. The caller updates runtime config only after return.
    """
    external_fernet = Fernet(external_key.encode())
    external_servers, external_dns = manager.split_payload(
        json.loads(external_fernet.decrypt(encrypted_data).decode('utf-8'))
    )
    app_data_dir = Path(manager.app_data_dir)
    config_path = app_data_dir / 'config.json'

    with profile_lock(app_data_dir):
        manager._check_profile_generation()
        config = read_config(config_path)
        saved_active = manager.get_active_data_path(config)
        runtime_active = manager.get_active_data_path(runtime_config)
        if 'active_data_file' in config and not _same_path(saved_active, runtime_active):
            raise VaultConflict('Active vault changed; reload before importing')
        active_file = saved_active or runtime_active

        if active_file:
            try:
                current_servers, current_dns = manager.read_payload(active_file)
            except InvalidToken as exc:
                raise CurrentVaultUnreadable('Current vault cannot be decrypted') from exc
        else:
            current_servers, current_dns = [], {}

        original_count = len(current_servers)
        merged = manager.merge_servers(current_servers, external_servers)
        merged_servers = merged['merged_servers']
        _reencrypt_server_secrets(merged_servers, original_count, external_fernet, manager)
        merged_dns, dns_added = dns_registry.merge(
            current_dns,
            external_dns,
            lambda value: _reencrypt_secret(value, external_fernet, manager),
        )

        target = app_data_dir / 'data' / ('merged_' + uuid.uuid4().hex + '.enc')
        manager.save_servers(
            merged_servers,
            str(target),
            dns={} if dns_registry.is_empty(merged_dns) else merged_dns,
        )
        config['active_data_file'] = str(target)
        try:
            write_config(config_path, config)
        except Exception:
            # Atomic replace may have succeeded before a directory fsync failed.
            # Follow the observed durable selection instead of splitting runtime and disk.
            committed = read_config(config_path)
            if not _same_path(manager.get_active_data_path(committed), target) or not target.is_file():
                raise
            config = committed
        return {
            'active_data_file': str(target),
            'added_count': merged['added_count'],
            'skipped_count': merged['skipped_count'],
            'dns_added': dns_added,
        }
