"""Resolve a server card and open a trusted SSH client with one auth policy."""
import logging

import paramiko

from .ssh_address import ssh_address
from .ssh_auth import connect_kwargs, has_ssh_auth
from .ssh_trust import RejectUnknownHost, load_known_hosts

logger = logging.getLogger(__name__)


def prepare_trusted_client(client):
    """Load the active trust store and reject every unknown SSH host key."""
    load_known_hosts(client)
    client.set_missing_host_key_policy(RejectUnknownHost())


def decrypt_card_auth(ssh_credentials, data_manager):
    """Return short lived SSH credentials decrypted from one server card."""
    def secret(field):
        value = ssh_credentials.get(field + '_decrypted', '')
        if not value and ssh_credentials.get(field):
            value = data_manager.decrypt_data(ssh_credentials[field])
        return value or ''

    return {
        'password': secret('password'),
        'key': secret('private_key'),
        'key_passphrase': secret('key_passphrase'),
    }


def resolve_server_ssh_credentials(server_id, data_manager, config):
    """Load one card, select its current address, and decrypt credentials for use."""
    servers = data_manager.load_servers(config)
    server = next((item for item in servers if str(item.get('id')) == str(server_id)), None)
    if not server:
        return None, None

    ssh_credentials = server.get('ssh_credentials', {})
    try:
        auth = decrypt_card_auth(ssh_credentials, data_manager)
    except Exception as exc:
        # Decryption errors can contain implementation details. Keep logs non-secret.
        logger.error('Failed to decrypt SSH credentials for server %s (%s)',
                     server_id, type(exc).__name__)
        return None, None

    port = ssh_credentials.get('port', 22)
    creds = {
        'ip': ssh_address(server, port),
        'user': ssh_credentials.get('user', 'root'),
        'password': auth['password'],
        'port': port,
    }
    if auth['key']:
        creds.update(key=auth['key'], key_passphrase=auth['key_passphrase'])
    return server, creds


def connect_card_client(client, creds, *, timeout=20, banner_timeout=None,
                        auth_timeout=None, local_keys_when_card_empty=False,
                        key_filename=None, key_passphrase=None):
    """Prepare strict host trust and connect with card credentials first.

    Local OpenSSH keys and ssh-agent are considered only when the card has neither
    a password nor a private key, and only when the caller allows that fallback.
    The caller owns the client lifecycle and must close it, including on failure.
    """
    prepare_trusted_client(client)
    use_local_keys = local_keys_when_card_empty and not has_ssh_auth(creds)
    auth = connect_kwargs(creds.get('password'), creds.get('key'),
                          creds.get('key_passphrase'), use_local_keys=use_local_keys)
    auth['key_filename'] = key_filename
    if key_filename and not creds.get('key'):
        if key_passphrase:
            auth['passphrase'] = key_passphrase
    from .ssh_service import SSHService
    SSHService.connect_managed(
        client,
        hostname=creds['ip'],
        port=int(creds.get('port', 22)),
        username=creds.get('user', 'root'),
        timeout=timeout,
        banner_timeout=banner_timeout if banner_timeout is not None else timeout,
        auth_timeout=auth_timeout if auth_timeout is not None else timeout,
        **auth,
    )
    return client
