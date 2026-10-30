"""Explicit, read-only import of the small OpenSSH config subset used by a card."""

from __future__ import annotations

import getpass
import os
import re
import shlex
from pathlib import Path

MAX_CONFIG_BYTES = 1024 * 1024
SUPPORTED = frozenset({'hostname', 'user', 'port', 'identityfile'})
_ALIAS = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z')
_HOST = re.compile(r'(?:[A-Za-z0-9][A-Za-z0-9_.:-]{0,252}|:[A-Fa-f0-9:]{1,252})\Z')
_USER = re.compile(r'[A-Za-z0-9_.-]{1,64}\Z')


class SSHConfigImportError(ValueError):
    """The explicitly requested local config could not be safely parsed."""


def _tokens(line):
    try:
        return shlex.split(line, comments=True, posix=True)
    except ValueError:
        return None


def _valid_value(name, value):
    if not value or '%' in value:
        return False
    if name == 'hostname':
        return bool(_HOST.fullmatch(value))
    if name == 'user':
        return bool(_USER.fullmatch(value))
    if name == 'port':
        try:
            return 1 <= int(value) <= 65535
        except ValueError:
            return False
    if name == 'identityfile' and value.startswith('~') and value != '~' and not value.startswith('~/'):
        return False
    return True


def _expanded_identity(path, home):
    if path == '~':
        expanded = str(home)
    elif path.startswith('~/'):
        expanded = os.path.join(str(home), path[2:])
    else:
        expanded = path
    if not os.path.isabs(expanded):
        expanded = os.path.join(str(home), expanded)
    return os.path.normpath(expanded)


def parse_ssh_config(text, home=None):
    """Return explicit aliases and safe fields; ignore and report other directives.

    Only literal Host aliases and the first literal value for HostName, User, Port,
    and IdentityFile are imported. Host patterns, Match sections, Include files,
    tokens and every other directive are reported without exposing their values.
    """
    if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_CONFIG_BYTES:
        raise SSHConfigImportError('config_too_large_or_invalid')
    home = Path(home or Path.home())
    global_values = {}
    scoped = []
    aliases = []
    unsupported_global = set()
    match_mode = False
    patterns = None

    for line_number, raw in enumerate(text.splitlines(), 1):
        def report_unsupported(value):
            entry = f'line {line_number}: {value}'
            if patterns is None:
                unsupported_global.add(entry)
            else:
                literal_patterns = [p for p in patterns if _ALIAS.fullmatch(p)]
                if literal_patterns:
                    scoped.append((literal_patterns, entry, '', line_number, True))
                else:
                    unsupported_global.add(entry + ' (Host pattern)')

        parts = _tokens(raw)
        if parts is None:
            report_unsupported('invalid quoting')
            continue
        if not parts:
            continue
        name = parts[0].lower()
        args = parts[1:]
        if name == 'host':
            match_mode = False
            patterns = args
            if not args:
                unsupported_global.add(f'line {line_number}: Host')
                continue
            for pattern in args:
                if pattern.startswith('!') or any(c in pattern for c in '*?['):
                    unsupported_global.add(f'line {line_number}: Host pattern')
                elif _ALIAS.fullmatch(pattern):
                    if pattern.lower() not in {item.lower() for item in aliases}:
                        aliases.append(pattern)
                else:
                    unsupported_global.add(f'line {line_number}: Host alias')
            continue
        if name == 'match':
            match_mode = True
            patterns = None
            unsupported_global.add(f'line {line_number}: Match')
            continue
        if name == 'include':
            unsupported_global.add(f'line {line_number}: Include')
            continue
        if match_mode:
            unsupported_global.add(f'line {line_number}: Match section')
            continue
        if name not in SUPPORTED:
            report_unsupported(parts[0])
            continue
        if len(args) != 1:
            report_unsupported(parts[0])
            continue
        value = args[0]
        if not _valid_value(name, value):
            report_unsupported(f'{parts[0]} value')
            continue
        if patterns is None:
            global_values.setdefault(name, []).append((value, line_number))
        else:
            scoped.append((patterns, name, value, line_number, False))

    hosts = []
    home_str = str(home)
    for alias in aliases:
        values = {key: list(items) for key, items in global_values.items()}
        unsupported = set()
        for patterns, name, value, line_number, is_unsupported in scoped:
            # Deliberately apply only literal aliases. Wildcard Host rules are
            # reported above rather than approximating OpenSSH's match semantics.
            if alias.lower() not in {p.lower() for p in patterns if _ALIAS.fullmatch(p)}:
                continue
            if is_unsupported:
                unsupported.add(name)
            else:
                values.setdefault(name, []).append((value, line_number))
        host_name = values.get('hostname', [(alias, 0)])[0][0]
        user = values.get('user', [(getpass.getuser(), 0)])[0][0]
        port = int(values.get('port', [('22', 0)])[0][0])
        identities = values.get('identityfile', [])
        identity_file = identities[0][0] if identities else None
        if identity_file and identity_file.lower() == 'none':
            identity_file = ''
        elif identity_file:
            identity_file = _expanded_identity(identity_file, home_str)
        if len(identities) > 1:
            unsupported.add('IdentityFile: only the first path can be imported')
        hosts.append({
            'alias': alias,
            'host_name': host_name,
            'user': user,
            'port': port,
            'identity_file': identity_file,
            'unsupported': sorted(unsupported),
        })

    return {'hosts': hosts, 'unsupported': sorted(unsupported_global)}


def read_local_ssh_config():
    """Read only the app user's ~/.ssh/config after an explicit UI request."""
    path = Path.home() / '.ssh' / 'config'
    try:
        with path.open('rb') as handle:
            raw = handle.read(MAX_CONFIG_BYTES + 1)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise SSHConfigImportError('config_unreadable') from exc
    if len(raw) > MAX_CONFIG_BYTES:
        raise SSHConfigImportError('config_too_large_or_invalid')
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise SSHConfigImportError('config_unreadable') from exc
    return parse_ssh_config(text, path.parent.parent)
