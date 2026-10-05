"""Small, strict adapter for TelegramOnly's generated NaiveProxy Caddyfile."""
import copy
import json
import re


def parse_caddyfile(raw):
    text = raw.decode('utf-8')
    auth = re.search(r'(?m)^\s*basic_auth\s+("(?:[^"\\]|\\.)*")\s+("(?:[^"\\]|\\.)*")\s*$', text)
    site = re.search(r'(?m)^:(\d+),\s+([^\s:]+):(\d+)\s*\{$', text)
    if not auth or not site or site.group(1) != site.group(3):
        raise ValueError('unsupported_config')
    username, password = json.loads(auth.group(1)), json.loads(auth.group(2))
    if not isinstance(username, str) or not isinstance(password, str) or not username or not password:
        raise ValueError('unsupported_config')
    return {'port': int(site.group(1)), 'domain': site.group(2), 'username': username, 'password': password}


def change_naive(manager, runtime, change):
    manager, runtime = copy.deepcopy(manager), copy.deepcopy(runtime)
    if not isinstance(manager, dict) or not isinstance(runtime, dict):
        raise ValueError('unsupported_config')
    fields = ('domain', 'username', 'password')
    if any(not isinstance(manager.get(key), str) or not manager[key] for key in fields) or type(manager.get('port')) is not int:
        raise ValueError('unsupported_config')
    if any(runtime.get(key) != manager.get(key) for key in ('domain', 'username', 'password')) or runtime.get('port') != manager['port']:
        raise ValueError('config_mismatch')
    if change.get('kind') == 'port' and type(change.get('port')) is int and 1 <= change['port'] <= 65535:
        manager['port'] = change['port']; runtime['port'] = change['port']; return manager, runtime
    if change.get('kind') in ('add_client', 'remove_client'):
        raise ValueError('shared_password')
    raise ValueError('invalid_change')


def replace_port(raw, domain, old_port, new_port):
    text = raw.decode('utf-8')
    pattern = rf'(?m)^(:){old_port}(,\s+{re.escape(domain)}:){old_port}(\s*\{{)$'
    updated, count = re.subn(pattern, rf'\g<1>{new_port}\g<2>{new_port}\g<3>', text)
    if count != 1: raise ValueError('target_changed')
    return updated.encode('utf-8')
