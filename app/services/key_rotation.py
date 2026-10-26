"""Re-encrypt into a new vault, then commit the profile with crash recovery."""
import io
import json
import uuid
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv.parser import parse_stream

from .config_io import read_config
from .data_manager_service import DataManagerService
from .dns_registry import SECRET_FIELDS
from .profile_transaction import commit_profile, profile_lock
from .vault_io import VaultConflict, VaultError, canonical


def _replace_key(raw, old_key, new_key):
    """Preserve unrelated dotenv settings; reject a different configured vault key."""
    output, replaced = [], False
    for binding in parse_stream(io.StringIO(raw.decode('utf-8'))):
        if binding.error:
            raise VaultError('Profile environment is malformed; key rotation was not started.')
        if binding.key == 'SECRET_KEY':
            if binding.value != old_key:
                raise VaultConflict('Profile key differs from the running application. Restart before changing it.')
            if not replaced:
                output.append('SECRET_KEY=' + new_key + '\n')
                replaced = True
        else:
            output.append(binding.original.string)
    text = ''.join(output)
    if not replaced:
        text = text.rstrip('\n') + '\nSECRET_KEY=' + new_key + '\n'
    return text.encode('utf-8')


def rotate_key(manager, active_file, new_key, data_dir=None):
    """No runtime state changes until all persistent files have committed."""
    Fernet(new_key.encode())
    directory = Path(manager.app_data_dir)
    with profile_lock(directory):
        manager._check_profile_generation()
        config = read_config(directory / 'config.json')
        if 'active_data_file' in config:
            selected = manager.get_active_data_path(config)
            if (canonical(selected) if selected else None) != (canonical(active_file) if active_file else None):
                raise VaultConflict('Active vault changed. Reload before changing the key.')
        try:
            old_env = (directory / '.env').read_bytes()
        except FileNotFoundError:
            old_env = b''
        new_env = _replace_key(old_env, manager.secret_key, new_key)
        # A selected but missing file is an error, never an empty new inventory.
        servers, dns = manager.read_payload(active_file) if active_file else ([], {})
        replacement = DataManagerService(new_key, str(directory))
        previous_cipher = manager.fernet
        def reencrypt(section, fields):
            if not isinstance(section, dict):
                raise VaultError('Invalid credentials structure. Key rotation was not started.')
            for field in fields:
                value = section.get(field)
                if value:
                    if not isinstance(value, str):
                        raise VaultError('Invalid credential value. Key rotation was not started.')
                    # Never copy an undecryptable inner secret to a vault with a different key.
                    plain = previous_cipher.decrypt(value.encode()).decode() if value.startswith('gAAAAA') else value
                    section[field] = replacement.encrypt_data(plain)
        for server in servers:
            for section, fields in (
                ('ssh_credentials', ('password', 'root_password', 'private_key', 'key_passphrase')),
                ('panel_credentials', ('user', 'password')),
                ('hoster_credentials', ('user', 'password')),
            ):
                reencrypt(server.get(section, {}), fields)
        for provider in dns.get('providers', []):
            reencrypt(provider, SECRET_FIELDS)
        target = Path(data_dir or directory / 'data') / ('servers_reencrypted_' + uuid.uuid4().hex + '.enc')
        replacement.save_servers(servers, str(target), dns=dns)
        replacement.read_payload(str(target))  # Validate before switching keys or active path.
        config['active_data_file'] = str(target)
        next_generation = uuid.uuid4().hex
        commit_profile(directory, new_env,
                       (json.dumps(config, ensure_ascii=False, indent=2) + '\n').encode(), next_generation)
        replacement.profile_generation = next_generation
        return replacement, str(target)
