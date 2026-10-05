"""Conservative protocol edits against a verified, dedicated sing-box service.

No Telegram imports. Passwords are generated on the VPS and never returned by
plans or apply responses. Unsupported/ambiguous installations remain read-only.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import stat
import tempfile
import time
import uuid

from .protocol_inspection import read_metadata, sources

ANYTLS_CONFIG = '/etc/anytls/config.json'
TUIC_CONFIG = '/etc/tuic/config.json'
XHTTP_CONFIG = '/etc/xhttp/config.json'
MUTATION_PROTOCOLS = ('anytls', 'tuic', 'xhttp')
MUTATION_BACKUPS = '/var/backups/vpn-server-manager'


def runtime_path(component):
    return {'anytls': ANYTLS_CONFIG, 'tuic': TUIC_CONFIG, 'xhttp': XHTTP_CONFIG}[component]


def mutation_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def validate_change(change):
    if not isinstance(change, dict):
        raise ValueError('invalid_change')
    operation = change.get('kind')
    if operation == 'port' and set(change) == {'kind', 'port'}:
        if type(change['port']) is int and 1 <= change['port'] <= 65535:
            return dict(change)
    if operation in ('add_client', 'remove_client') and set(change) == {'kind', 'name'}:
        name = change['name']
        if isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', name):
            return dict(change)
    raise ValueError('invalid_change')


def changed_anytls(manager, runtime, change, *, password=None):
    return changed_protocol('anytls', manager, runtime, change, password=password)


def changed_protocol(component, manager, runtime, change, *, password=None, client_uuid=None):
    if component not in MUTATION_PROTOCOLS:
        raise ValueError('unsupported_config')
    manager, runtime = copy.deepcopy(manager), copy.deepcopy(runtime)
    clients = manager.get('clients')
    inbounds = runtime.get('inbounds')
    if not isinstance(clients, list) or not clients or len(clients) > 9999:
        raise ValueError('unsupported_config')
    inbound_type = 'vless' if component == 'xhttp' else component
    if not isinstance(inbounds, list) or len(inbounds) != 1 or not isinstance(inbounds[0], dict) or inbounds[0].get('type') != inbound_type:
        raise ValueError('unsupported_config')
    inbound = inbounds[0]
    names = set()
    identifiers = set()
    fields = ('name', 'uuid') if component == 'xhttp' else ('name', 'uuid', 'password') if component == 'tuic' else ('name', 'password')
    expected = []
    for client in clients:
        if not isinstance(client, dict) or not isinstance(client.get('name'), str) or not client['name'] or client['name'] in names:
            raise ValueError('unsupported_config')
        if any(not isinstance(client.get(field), str) or not client[field] for field in fields):
            raise ValueError('unsupported_config')
        if 'uuid' in fields:
            try: identifier = str(uuid.UUID(client['uuid']))
            except (ValueError, AttributeError): raise ValueError('unsupported_config') from None
            if identifier in identifiers: raise ValueError('unsupported_config')
            identifiers.add(identifier)
        names.add(client['name'])
        expected.append({field: client[field] for field in fields})
    # WARNING: Editing a manager file alone can revoke access only on paper.
    # Require agreement with the exact runtime file before changing either.
    users = inbound.get('users')
    if not isinstance(users, list) or not all(isinstance(u, dict) and isinstance(u.get('name'), str) for u in users) or sorted(users, key=lambda u: u['name']) != sorted(expected, key=lambda u: u['name']):
        raise ValueError('config_mismatch')
    if type(manager.get('port')) is not int or inbound.get('listen_port') != manager['port']:
        raise ValueError('config_mismatch')
    tls = inbound.get('tls', {})
    security = manager.get('security', 'tls') if component == 'xhttp' else 'tls'
    if security not in ('tls', 'none') or not isinstance(tls, dict) or tls.get('enabled') is not (security == 'tls'):
        raise ValueError('config_mismatch')
    if security == 'tls' and (tls.get('certificate_path') != manager.get('tls_cert_path', f'/etc/{component}/server.crt') or tls.get('key_path') != manager.get('tls_key_path', f'/etc/{component}/server.key')):
        raise ValueError('config_mismatch')
    if component == 'tuic':
        if inbound.get('congestion_control', 'bbr') != manager.get('congestion_control', 'bbr') or tls.get('alpn', []) != manager.get('alpn', ['h3']):
            raise ValueError('config_mismatch')
    if component == 'xhttp':
        transport = inbound.get('transport')
        if not isinstance(transport, dict) or transport.get('type') != 'xhttp' or transport.get('path') != manager.get('path', '/') or transport.get('mode', 'auto') != manager.get('mode', 'auto') or transport.get('host', '') != manager.get('host', ''):
            raise ValueError('config_mismatch')
    change = validate_change(change)
    if change['kind'] == 'port':
        manager['port'] = inbound['listen_port'] = change['port']
    elif change['kind'] == 'add_client':
        if change['name'] in names: raise ValueError('client_exists')
        client = {'name': change['name']}
        if 'password' in fields: client['password'] = password or 'validation-only'
        if 'uuid' in fields:
            client['uuid'] = client_uuid or '00000000-0000-4000-8000-000000000000'
            if str(uuid.UUID(client['uuid'])) in identifiers: raise ValueError('client_exists')
        manager['clients'].append(client)
    else:
        if change['name'] not in names: raise ValueError('client_missing')
        if len(clients) == 1: raise ValueError('last_client')
        manager['clients'] = [c for c in clients if c['name'] != change['name']]
    inbound['users'] = [{field: c[field] for field in fields} for c in manager['clients']]
    return manager, runtime


def prepare_mutation(body, inventory, run):
    component = body.get('component')
    if component not in MUTATION_PROTOCOLS: raise ValueError('unsupported_config')
    config_path = runtime_path(component)
    if (Path(MUTATION_BACKUPS) / f'{component}-pending.json').exists():
        raise ValueError('recovery_required')
    change = validate_change(body.get('change'))
    if any(c['key'] == 'bot' and any(i['state'] not in ('inactive', 'exited', 'created', 'failed') for i in c['instances']) for c in inventory['components']):
        raise ValueError('bot_running')
    instances = [i for c in inventory['components'] if c['key'] == component for i in c['instances']]
    if len(instances) != 1 or instances[0]['runtime'] != 'systemd' or instances[0]['state'] != 'active':
        raise ValueError('unsupported_runtime')
    instance = instances[0]
    found = {}
    for path, _ in sources(inventory, run)[component]:
        try: data, revision = read_metadata(path)
        except FileNotFoundError: continue
        found[path] = (data, revision)
    if len(found) != 1: raise ValueError('ambiguous_config')
    path, (manager, revision) = next(iter(found.items()))
    if hashlib.sha256(path.encode()).hexdigest() != body.get('source_id') or revision != body.get('revision'):
        raise ValueError('target_changed')
    code, raw = run(['systemctl', 'show', instance['id'], '--property=ExecStart', '--value'])
    match = re.fullmatch(r'\{ path=([^ ;]+) ; argv\[\]=(.*?) ; .*?\}', raw.strip()) if code == 0 else None
    if not match: raise ValueError('unsupported_runtime')
    executable = match[1]
    if executable not in ('/usr/bin/sing-box', '/usr/local/bin/sing-box'):
        raise ValueError('unsupported_runtime')
    if shlex.split(match[2]) != [executable, 'run', '-c', config_path]:
        raise ValueError('unsupported_runtime')
    runtime, runtime_revision = read_metadata(config_path)
    changed_protocol(component, manager, runtime, change)
    public = {'hostname': inventory['hostname'], 'component': component, 'action': 'configure',
              'target': instance, 'change': change, 'source_id': body['source_id'],
              'revision': revision, 'runtime_revision': runtime_revision,
              'unit_revision': hashlib.sha256(raw.encode()).hexdigest()}
    public['plan_hash'] = mutation_digest(public)
    return public, path, manager, runtime, executable


def private_directory(path):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('unsafe_path')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError('unsafe_path')
    return path


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def service_healthy(unit, run):
    # An immediately active process can still fail during initialization.
    for delay in (0, 1, 2):
        if delay: time.sleep(delay)
        code, state = run(['systemctl', 'is-active', '--', unit])
        if code or state.strip() != 'active': return False
    return True


def snapshot(path):
    # Parent directories must not be writable by other accounts.
    path = Path(path)
    for parent in path.parents:
        info = parent.stat()
        if parent.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('unsafe_path')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o022 or info.st_size > 1048576:
            raise ValueError('unsafe_path')
        raw = os.read(fd, 1048577)
        if len(raw) > 1048576: raise ValueError('invalid_file')
        return raw, info
    finally:
        os.close(fd)


def durable_replace(path, raw, info):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.vpn-manager-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), stat.S_IMODE(info.st_mode))
            os.fchown(stream.fileno(), info.st_uid, info.st_gid)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def apply_mutation(body, inventory, run, rediscover):
    plan, source, manager, runtime, executable = prepare_mutation(body, inventory, run)
    if plan['plan_hash'] != body.get('plan_hash') or plan['hostname'] != body.get('confirmation'):
        raise ValueError('target_changed')
    config_path = runtime_path(plan['component'])
    originals = {p: snapshot(p) for p in (source, config_path)}
    if hashlib.sha256(originals[source][0]).hexdigest() != plan['revision'] or hashlib.sha256(originals[config_path][0]).hexdigest() != plan['runtime_revision']:
        raise ValueError('target_changed')
    updated_manager, updated_runtime = changed_protocol(plan['component'], manager, runtime, plan['change'], password=secrets.token_urlsafe(32), client_uuid=str(uuid.uuid4()))
    replacements = {source: json.dumps(updated_manager, ensure_ascii=False, indent=2).encode(),
                    config_path: json.dumps(updated_runtime, ensure_ascii=False, indent=2).encode()}
    backup_root = private_directory(MUTATION_BACKUPS)
    backup = private_directory(backup_root / (time.strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(6)))
    for index, (path, (raw, info)) in enumerate(originals.items()):
        with (backup / f'{index}.json').open('xb') as stream:
            os.chmod(stream.name, 0o600)
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    with (backup / 'manifest.json').open('x', encoding='utf-8') as stream:
        os.chmod(stream.name, 0o600)
        json.dump({'unit': plan['target']['id'], 'files': [
            {'path': path, 'backup': f'{index}.json', 'sha256': hashlib.sha256(raw).hexdigest(),
             'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid, 'gid': info.st_gid}
            for index, (path, (raw, info)) in enumerate(originals.items())]}, stream)
        stream.flush(); os.fsync(stream.fileno())
    candidate = backup / 'candidate.json'
    with candidate.open('xb') as stream:
        os.chmod(stream.name, 0o600)
        stream.write(replacements[config_path]); stream.flush(); os.fsync(stream.fileno())
    sync_directory(backup)
    sync_directory(backup_root)
    code, _ = run([executable, 'check', '-c', str(candidate)])
    if code: return {'success': False, 'error': 'validation_failed'}
    # Recheck service, bot and file revisions after potentially slow validation.
    current = prepare_mutation(body, rediscover(), run)[0]
    if current['plan_hash'] != plan['plan_hash']: raise ValueError('target_changed')
    marker = backup_root / f'{plan["component"]}-pending.json'
    with marker.open('x', encoding='utf-8') as stream:
        os.chmod(marker, 0o600)
        json.dump({'backup': str(backup), 'files': list(originals), 'unit': plan['target']['id']}, stream)
        stream.flush(); os.fsync(stream.fileno())
    sync_directory(backup_root)
    written = []
    try:
        for path, raw in replacements.items():
            if snapshot(path)[0] != originals[path][0]: raise ValueError('target_changed')
            # Include the file before rename, so a later fsync error also rolls back.
            written.append(path)
            durable_replace(path, raw, originals[path][1])
        code, _ = run(['systemctl', 'restart', '--', plan['target']['id']])
        if code or not service_healthy(plan['target']['id'], run): raise ValueError('restart_failed')
        if any(snapshot(p)[0] != raw for p, raw in replacements.items()): raise ValueError('target_changed')
        updated_inventory = rediscover()
        marker.unlink()
        sync_directory(backup_root)
        return {'success': True, 'backup': str(backup), 'inventory': updated_inventory}
    except Exception:
        try:
            if not written:
                marker.unlink()
                sync_directory(backup_root)
                return {'success': False, 'error': 'target_changed', 'backup': str(backup)}
            # A concurrent edit to an unwritten file is also a conflict: do not
            # restart the service using a configuration we did not validate.
            for path in originals:
                allowed = (originals[path][0], replacements[path]) if path in written else (originals[path][0],)
                if snapshot(path)[0] not in allowed: raise ValueError('external_change')
            for path in reversed(written):
                if snapshot(path)[0] not in (replacements[path], originals[path][0]):
                    raise ValueError('external_change')
                durable_replace(path, originals[path][0], originals[path][1])
            code, _ = run(['systemctl', 'restart', '--', plan['target']['id']])
            if code or not service_healthy(plan['target']['id'], run): raise ValueError('recovery_required')
            marker.unlink(missing_ok=True)
            sync_directory(backup_root)
            return {'success': False, 'error': 'rolled_back', 'backup': str(backup)}
        except Exception:
            return {'success': False, 'error': 'recovery_required', 'backup': str(backup)}
