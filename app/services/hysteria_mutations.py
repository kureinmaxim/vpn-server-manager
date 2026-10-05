"""Restricted TelegramOnly YAML adapter; no dependency or service execution.

Reject YAML features that cannot be round-tripped with this small mapping-only
format. This is structural validation, not a native Hysteria startup check.
"""
import copy
import json
import re


def hysteria_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key.lower() in {k.lower() for k in result}: raise ValueError('unsupported_config')
        result[key] = value
    return result


def parse_hysteria(raw):
    text = raw.decode('utf-8')
    if text.lstrip().startswith('{'):
        data = json.loads(text, object_pairs_hook=hysteria_pairs)
        if not isinstance(data, dict): raise ValueError('unsupported_config')
        return data
    root = {}
    stack = [(-2, root)]
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'): continue
        if '\t' in line: raise ValueError('unsupported_config')
        indent = len(line) - len(line.lstrip(' '))
        if indent % 2 or indent > 32: raise ValueError('unsupported_config')
        match = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_.-]*):(?: (.*))?', line.strip())
        if not match: raise ValueError('unsupported_config')
        key, value = match.groups()
        while stack[-1][0] >= indent: stack.pop()
        if indent != stack[-1][0] + 2: raise ValueError('unsupported_config')
        parent = stack[-1][1]
        if key.lower() in {k.lower() for k in parent}: raise ValueError('unsupported_config')
        if value is None or value == '':
            parent[key] = {}; stack.append((indent, parent[key])); continue
        if value.startswith('"') or value in ('true', 'false') or re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?', value):
            scalar = json.loads(value)
            if not isinstance(scalar, (str, int, float, bool)): raise ValueError('unsupported_config')
        elif re.fullmatch(r'[A-Za-z0-9_/.:@+-]+', value) and value.lower() not in ('true', 'false', 'yes', 'no', 'on', 'off', 'null', '~') and not re.match(r'^[+\-0-9.]', value):
            scalar = value
        else: raise ValueError('unsupported_config')
        parent[key] = scalar
    if not root: raise ValueError('unsupported_config')
    return root


def changed_hysteria(manager, runtime, change, *, password=None):
    manager, runtime = copy.deepcopy(manager), copy.deepcopy(runtime)
    port = manager.get('port')
    if type(port) is not int or not 1 <= port <= 65535 or runtime.get('listen') != f':{port}':
        raise ValueError('config_mismatch')
    tls = runtime.get('tls')
    if not isinstance(tls, dict) or tls.get('cert') != manager.get('tls_cert_path', '/etc/hysteria/server.crt') or tls.get('key') != manager.get('tls_key_path', '/etc/hysteria/server.key') or 'acme' in runtime:
        raise ValueError('config_mismatch')
    expected_obfs = {}
    if manager.get('obfs_type'):
        if manager['obfs_type'] != 'salamander' or not manager.get('obfs_password'): raise ValueError('unsupported_config')
        expected_obfs = {'type':'salamander', 'salamander':{'password':manager['obfs_password']}}
    if runtime.get('obfs', {}) != expected_obfs: raise ValueError('config_mismatch')
    clients = manager.get('clients', [])
    if not isinstance(clients, list) or len(clients) > 9999: raise ValueError('unsupported_config')
    users = {}
    for client in clients:
        # Viper normalizes mapping keys; avoid creating a profile with a username
        # whose case does not match the effective userpass map.
        if not isinstance(client, dict) or not isinstance(client.get('name'), str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', client['name']) or client['name'] in users or not isinstance(client.get('password'), str) or not client['password']:
            raise ValueError('unsupported_config')
        users[client['name']] = client['password']
    # WARNING: TelegramOnly restores default from its root password on read.
    # Reject mismatches and protect default from a revoke that would not persist.
    if clients and manager.get('password') and users.get('default') != manager['password']:
        raise ValueError('config_mismatch')
    expected_auth = {'type':'userpass', 'userpass':users} if clients else {'type':'password', 'password':manager.get('password')}
    if (not clients and (not isinstance(manager.get('password'), str) or not manager['password'])) or runtime.get('auth') != expected_auth:
        raise ValueError('config_mismatch')
    if change['kind'] == 'port':
        manager['port'] = change['port']; runtime['listen'] = f':{change["port"]}'
    elif not clients:
        raise ValueError('shared_password')
    elif change['kind'] == 'add_client':
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', change['name']): raise ValueError('invalid_change')
        if change['name'] in users: raise ValueError('client_exists')
        manager['clients'].append({'name':change['name'], 'password':password or 'validation-only'})
    else:
        if change['name'] not in users: raise ValueError('client_missing')
        if len(clients) == 1: raise ValueError('last_client')
        if change['name'] == 'default': raise ValueError('protected_client')
        manager['clients'] = [c for c in clients if c['name'] != change['name']]
    if clients:
        runtime['auth']['userpass'] = {c['name']:c['password'] for c in manager['clients']}
    return manager, runtime
