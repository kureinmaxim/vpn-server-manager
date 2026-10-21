"""Application boundary for the isolated, read-only SSH probe."""
import base64
import json
import threading
import time
from collections import OrderedDict
from pathlib import Path

from .dns_mail_probe import ROLE_NAMES, ProbeError, domain

DEFAULTS = {'role': 'adguard', 'query': 'example.com', 'expected': 'NOERROR',
            'dns_port': 5300, 'doh_port': 3001, 'doh_file': '/root/dns-doh-url',
            'mail_domain': '', 'smtp_port': 25, 'submission_port': 587,
            'smtps_port': 465, 'imap_port': 143, 'imaps_port': 993,
            'turn_port': 3478, 'iroh_port': 3340}
_checks = OrderedDict()
_lock = threading.Lock()


def cache_key(client):
    # Connection identity stays in memory; never returned to the browser.
    return tuple(client.get_transport().getpeername())


def remember(client, config, results):
    primary = [r for r in results if r['name'] not in ('TURN / STUN', 'iroh TCP')]
    states = {r['state'] for r in primary}
    state = (next(iter(states)) if len(states) == 1 else 'partial') if states else 'unconfigured'
    with _lock:
        key = (cache_key(client), config['role'])
        _checks[key] = {'state': state, 'checked_at': results[0]['checked_at'] if results else None,
                        'time': time.monotonic(), 'source': 'ssh'}
        _checks.move_to_end(key)
        while len(_checks) > 128:
            _checks.popitem(last=False)


def annotate(client, roles):
    try:
        identity = cache_key(client)
        with _lock:
            for role in roles:
                previous = _checks.get((identity, role['key']))
                if previous:
                    role['last_check'] = {k: v for k, v in previous.items() if k != 'time'}
                    role['last_check']['stale'] = time.monotonic() - previous['time'] > 300
    except Exception:
        pass  # No history is preferable to losing current discovery results.


def settings(data):
    """Strict allowlist: never accept a URL/password in the configuration."""
    if not isinstance(data, dict) or set(data) - set(DEFAULTS):
        raise ValueError('configuration')
    result = dict(DEFAULTS, **data)
    if (not isinstance(result['role'], str) or result['role'] not in ROLE_NAMES
            or result['expected'] not in ('NOERROR', 'NXDOMAIN')
            or not isinstance(result['mail_domain'], str)):
        raise ValueError('configuration')
    try:
        result['query'] = domain(result['query'])
        result['mail_domain'] = domain(result['mail_domain']) if result['mail_domain'] else ''
    except (ProbeError, UnicodeError):
        raise ValueError('configuration') from None
    path = result['doh_file']
    if (not isinstance(path, str) or not path.startswith('/') or len(path) > 256
            or '..' in path.split('/') or any(ord(c) < 33 for c in path) or '://' in path):
        raise ValueError('configuration')
    for key in DEFAULTS:
        if key.endswith('_port'):
            value = result[key]
            if isinstance(value, bool) or not str(value).isdigit():
                raise ValueError('configuration')
            result[key] = int(value)
            if not (1 if key in ('dns_port', 'doh_port') else 0) <= result[key] <= 65535:
                raise ValueError('configuration')
    return result


def remote_probe(client, config=None):
    source = Path(__file__).with_name('dns_mail_probe.py').read_bytes()
    encoded = base64.b64encode(source).decode('ascii')
    command = "python3 -c \"import base64;exec(compile(base64.b64decode('" + encoded + "'),'<diagnostic>','exec'))\""
    stdin, stdout, stderr = client.exec_command(command, timeout=35 if config else 12)
    try:
        stdin.write(json.dumps(config if config is not None else {'mode': 'discover'}))
        stdin.flush()
        stdin.channel.shutdown_write()
        raw = stdout.read(131073)
        if len(raw) > 131072:
            raise ValueError('probe_unavailable')
        result = json.loads(raw)
        if not isinstance(result, list):
            raise ValueError('probe_unavailable')
        return result
    finally:
        # Do not read/return stderr: third party errors can contain sensitive text.
        stdout.channel.close()


def discovery_rows(client):
    try:
        roles = remote_probe(client)
        annotate(client, roles)
    except Exception:
        roles = [dict(key=key, name=name, detected=False, state='unknown',
                      discovery='unavailable', components=[], source='ssh', functional='unconfigured')
                 for key, name in ROLE_NAMES.items()]
    return [dict(name=role['name'], display_name=role['name'], kind='role', group='project',
                 project=role['key'], project_name=role['name'], status='unknown',
                 control_component=None, role_summary=role) for role in roles]
