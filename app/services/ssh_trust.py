"""Strict host identity checks and safe, translated public-key diagnostics."""
import hashlib
import os
import re
from pathlib import Path

import paramiko
from flask_babel import gettext as _
from .ssh_auth import fingerprint


class KnownHostsError(paramiko.SSHException):
    pass


class UnknownHostKeyError(paramiko.SSHException):
    def __init__(self, hostname, key=None):
        super().__init__('Unknown SSH host key')
        self.hostname = hostname
        self.key = key


class RejectUnknownHost(paramiko.RejectPolicy):
    def missing_host_key(self, client, hostname, key):
        raise UnknownHostKeyError(hostname, key)


def trust_revision():
    try:
        raw = Path(os.path.expanduser('~/.ssh/known_hosts')).read_bytes()
    except FileNotFoundError:
        raw = b''
    except OSError as exc:
        raise KnownHostsError('Cannot read known_hosts') from exc
    return hashlib.sha256(raw).digest()


def load_known_hosts(client):
    from .ssh_service import SSHService
    revision = SSHService.refresh_trust()
    try:
        path = Path(os.path.expanduser('~/.ssh/known_hosts'))
        if path.exists():
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('@') or paramiko.hostkeys.HostKeyEntry.from_line(line, number) is None:
                    raise ValueError('Unsupported or malformed host-key entry')
        client.load_system_host_keys()
    except Exception as exc:
        SSHService.close_all()
        raise KnownHostsError('Cannot parse known_hosts') from exc
    if trust_revision() != revision:
        from .ssh_service import SSHSessionInvalidated
        raise SSHSessionInvalidated()
    client._vpn_trust_revision = revision


def _fingerprint(key):
    return fingerprint(key) if isinstance(key, paramiko.PKey) else '—'


def _endpoint(value):
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.:\[\]-]{1,300}', value) else '—'


def host_key_message(error):
    # Wrappers retain the original typed exception, never expose its raw text.
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if getattr(error, 'reason', None) == 'connection_changed':
            return _('Параметры SSH изменились. Повторите проверку с актуальными данными карточки.')
        if isinstance(error, KnownHostsError):
            return _('Не удалось прочитать known_hosts. Проверьте права и формат файла; проверка ключей не отключена.')
        if isinstance(error, UnknownHostKeyError):
            return _('SSH %(endpoint)s: ключ сервера неизвестен. Получен %(received)s. Сверьте отпечаток через независимый доверенный канал, затем сохраните проверенный ключ в known_hosts через OpenSSH.',
                     endpoint=_endpoint(error.hostname), received=_fingerprint(error.key))
        if isinstance(error, paramiko.BadHostKeyException):
            return _('SSH %(endpoint)s: ключ сервера изменился. Ожидался %(expected)s; получен %(received)s. Подключение отклонено. Проверьте причину смены через независимый канал; не удаляйте старую запись вслепую.',
                     endpoint=_endpoint(error.hostname), expected=_fingerprint(error.expected_key), received=_fingerprint(error.key))
        error = error.__cause__ or error.__context__
    return None
