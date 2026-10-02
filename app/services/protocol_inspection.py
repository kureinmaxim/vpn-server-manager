"""Read-only TelegramOnly configuration discovery; standard library only.

This module is bundled into the SSH payload. Source metadata is not treated as
proof of effective runtime configuration, and secret values are never returned.
"""
import hashlib
import json
import os
import posixpath
import stat
from pathlib import Path

PROTOCOL_FILES = {key: key + '_config.json' for key in (
    'vless', 'hysteria2', 'naiveproxy', 'mieru', 'mtproto', 'tuic', 'anytls', 'xhttp')}
DEFAULT_ROOTS = ('/opt/TelegramOnly', '/opt/TelegramSimple', '/var/lib/vpn-server-manager')
PUBLIC_FIELDS = {
    'enabled': bool, 'server': str, 'domain': str, 'port': int, 'sni': str,
    'insecure': bool, 'transport': str, 'mode': str, 'security': str,
}


def read_metadata(path):
    """Bounded regular-file read, refusing symlinks (including parent directories)."""
    path = Path(path)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('unsafe_path')
    fd = os.open(str(path), os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 1024 * 1024:
            raise ValueError('invalid_file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError('invalid_file')
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError('invalid_file')
        return data, hashlib.sha256(raw).hexdigest()
    finally:
        os.close(fd)


def summarize(data):
    # Allowlist rather than a password blacklist: future fields stay private.
    fields = {key: value for key, kind in PUBLIC_FIELDS.items()
              if type(value := data.get(key)) is kind and (not isinstance(value, str) or len(value) <= 255)}
    clients = data.get('clients')
    result = {'fields': fields, 'client_count': len(clients) if isinstance(clients, list) else None}
    if not clients and data.get('password'):
        # Legacy shared credentials (NaiveProxy / Hysteria2); never return them.
        result['client_count'] = 1
    if isinstance(data.get('port_bindings'), list):
        result['ports'] = [{'port': row['port'], 'protocol': row['protocol']}
                           for row in data['port_bindings'] if isinstance(row, dict)
                           and type(row.get('port')) is int and 1 <= row['port'] <= 65535
                           and row.get('protocol') in ('TCP', 'UDP')][:64]
    return result


def sources(inventory, run):
    """Find manager files, including bind mounts of a stopped Docker bot.

    No environment dump, docker exec or importing bot modules (which may write).
    """
    roots = {root: 'candidate' for root in DEFAULT_ROOTS}
    mounted = {key: [] for key in PROTOCOL_FILES}
    for component in inventory['components']:
        if component['key'] != 'bot':
            continue
        for instance in component['instances']:
            if instance['runtime'] == 'systemd':
                code, raw = run(['systemctl', 'show', instance['id'], '--property=WorkingDirectory', '--value'])
                directory = raw.strip()
                if code == 0 and directory.startswith('/') and '\n' not in directory and len(directory) < 4096:
                    roots[directory] = 'telegramonly-systemd'
            elif instance['runtime'] == 'docker':
                code, raw = run(['docker', 'inspect', '--format', '{{json .Mounts}}', instance['id']])
                try:
                    mounts = json.loads(raw) if code == 0 else []
                    if not isinstance(mounts, list):
                        continue
                    for mount in mounts:
                        if not isinstance(mount, dict) or mount.get('Type') != 'bind':
                            continue
                        source, destination = mount.get('Source'), mount.get('Destination')
                        if not isinstance(source, str) or not isinstance(destination, str) or not source.startswith('/'):
                            continue
                        for key, name in PROTOCOL_FILES.items():
                            if destination.rstrip('/').endswith('/' + name):
                                mounted[key].append((source, 'telegramonly-docker'))
                        # Directory mounts cover all manager files, regardless of
                        # the path used inside the container.
                        if Path(source).is_dir():
                            roots[source] = 'telegramonly-docker'
                except (ValueError, TypeError):
                    continue
    for key, name in PROTOCOL_FILES.items():
        mounted[key].extend((posixpath.join(root, name), owner) for root, owner in roots.items())
    return mounted


def inspect_protocols(inventory, run):
    candidates = sources(inventory, run)
    result = []
    xui = any(c['key'] == 'xui' and c['instances'] for c in inventory['components'])
    for key in PROTOCOL_FILES:
        found, seen = [], set()
        for path, owner in candidates[key]:
            if path in seen:
                continue
            seen.add(path)
            try:
                data, revision = read_metadata(path)
                found.append(dict(path=path, owner=owner, revision=revision,
                                  source_id=hashlib.sha256(path.encode('utf-8')).hexdigest(), **summarize(data)))
            except FileNotFoundError:
                continue
            except (ValueError, OSError):
                # Do not return decoder excerpts or arbitrary exception messages.
                found.append(dict(path=path, owner=owner, error='unreadable'))
        ownership = 'ambiguous' if len(found) > 1 else (found[0]['owner'] if found else 'not_found')
        if key == 'vless' and xui:
            ownership = 'xui_detected'
        result.append({'key': key, 'ownership': ownership, 'sources': found})
    return {'hostname': inventory['hostname'], 'protocols': result}
