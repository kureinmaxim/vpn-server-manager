"""Вход по SSH: пароль и/или ключ из карточки сервера.

Все подключения приложения берут параметры входа из connect_kwargs(). Если в
карточке есть и ключ, и пароль, paramiko сначала пробует ключ, затем пароль.
Ключ хранится в карточке зашифрованным, как пароль: путь к файлу на этой машине
(например ~/.ssh/id_ed25519) или содержимое приватного ключа.
"""
from __future__ import annotations

import base64
import hashlib
import io
import os
from typing import Any, Dict, Optional

import paramiko

# DSA (ssh-dss) paramiko больше не поддерживает, и OpenSSH отключил его по умолчанию.
KEY_CLASSES = (paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.RSAKey)
MAX_KEY_BYTES = 64 * 1024


class SshKeyError(paramiko.AuthenticationException):
    """Ключ не прочитан. Наследник AuthenticationException: существующие обработчики
    показывают его как ошибку входа, не раскрывая содержимого ключа."""


def is_key_text(value: Optional[str]) -> bool:
    """Вставлено содержимое ключа, а не путь к файлу."""
    return (value or '').lstrip().startswith('-----BEGIN')


def _read_key_text(value: str) -> str:
    if is_key_text(value):
        return value
    path = os.path.expanduser(value.strip())
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return handle.read(MAX_KEY_BYTES)
    except (OSError, UnicodeDecodeError) as exc:
        raise SshKeyError('SSH key file is not readable') from exc


def load_private_key(value: str, passphrase: Optional[str] = None) -> paramiko.PKey:
    """Приватный ключ из пути или текста. Тип определяется перебором поддерживаемых."""
    text = _read_key_text(value)
    for key_class in KEY_CLASSES:
        try:
            return key_class.from_private_key(io.StringIO(text), password=passphrase or None)
        except paramiko.PasswordRequiredException as exc:
            raise SshKeyError('SSH key is encrypted: passphrase required') from exc
        except (paramiko.SSHException, ValueError, TypeError, IndexError):
            continue
    raise SshKeyError('SSH key is not readable: unsupported format or wrong passphrase')


def fingerprint(key: paramiko.PKey) -> str:
    """Как у `ssh-keygen -lf`: «ssh-ed25519 SHA256:…» — для карточки, не секрет."""
    digest = base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode('ascii').rstrip('=')
    return f'{key.get_name()} SHA256:{digest}'


def connect_kwargs(password: Optional[str] = None, key: Optional[str] = None,
                   key_passphrase: Optional[str] = None, *,
                   use_local_keys: bool = False) -> Dict[str, Any]:
    """Параметры paramiko.SSHClient.connect для входа.

    use_local_keys=False (по умолчанию) — только то, что в карточке: без ~/.ssh и
    ssh-agent, чтобы не было неожиданных входов и медленного перебора ключей.
    """
    kwargs: Dict[str, Any] = {
        'password': password or None,
        'look_for_keys': use_local_keys,
        'allow_agent': use_local_keys,
    }
    if key:
        kwargs['pkey'] = load_private_key(key, key_passphrase)
    return kwargs


def has_ssh_auth(creds: Optional[Dict[str, Any]]) -> bool:
    """В карточке есть чем войти: пароль или ключ."""
    return bool(creds and (creds.get('password') or creds.get('key')))
