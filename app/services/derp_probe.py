"""Standalone stdlib-only remote probe. Prints an allowlisted report, never config."""
import ipaddress
import json
import re
import shlex
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit


def read_config(text):
    """Read conventional block YAML without loading tags, aliases or secret fields.

    Complex YAML is deliberately unavailable; no guessed enabled/free states.
    """
    stack, values, seen = [], {}, set()
    relevant = False
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'): continue
        if '\t' in line or line.lstrip().startswith(('---', '...')): raise ValueError('unsupported YAML')
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            relevant = bool(re.match(r'(derp|server_url):', line))
        if not relevant: continue
        while stack and stack[-1][0] >= indent: stack.pop()
        path = tuple(item[1] for item in stack)
        stripped = line.strip()
        if stripped.startswith('- '):
            if path == ('derp', 'urls'):
                values['has_urls'] = True
                value = shlex.split(stripped[2:], comments=True)
                if value and urlsplit(value[0]).hostname == 'controlplane.tailscale.com': values['public_map'] = True
            continue
        match = re.match(r'([a-zA-Z_][\w-]*):(?:\s+(.*)|\s*)$', stripped)
        if not match: raise ValueError('unsupported YAML')
        key, raw = match.group(1), match.group(2) or ''
        full = path + (key,)
        if full in seen: raise ValueError('duplicate YAML key')
        seen.add(full)
        tokens = shlex.split(raw, comments=True)
        if not tokens:
            stack.append((indent, key))
            continue
        value = ' '.join(tokens)
        if full == ('server_url',): values['probe_host'] = urlsplit(value).hostname or ''
        if full == ('derp', 'urls'):
            if value != '[]': raise ValueError('unsupported URL list')
            values.update(has_urls=False, public_map=False)
        if path == ('derp', 'server') and key in (
                'enabled', 'region_id', 'region_code', 'region_name',
                'stun_listen_addr', 'verify_clients', 'ipv4'):
            if value.startswith(('&', '*', '!', '|', '>', '{', '[')): raise ValueError('unsupported scalar')
            if key in ('enabled', 'verify_clients'):
                if value.lower() not in ('true', 'false'): raise ValueError('invalid boolean')
                value = value.lower() == 'true'
            elif key == 'region_id': value = int(value)
            values[key] = value
    if ('derp',) not in seen: raise ValueError('missing DERP section')
    values.setdefault('has_urls', False if ('derp', 'urls') in seen else None)
    values.setdefault('public_map', False if ('derp', 'urls') in seen else None)
    return values


def collect():
    deadline = time.monotonic() + 10
    def command(args, timeout=2):
        remaining = deadline - time.monotonic()
        if remaining <= 0: return None
        try:
            result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    timeout=min(timeout, remaining), text=True, encoding='utf-8', errors='replace')
            if result.returncode == 0 and len(result.stdout) <= 262144: return result.stdout
        except (OSError, subprocess.SubprocessError): pass
        return None

    report = {'state': 'ready', 'headscale': None, 'version': '', 'config': None,
              'probe_code': None, 'stun_port': 3478, 'stun_listening': None,
              'tcp443_busy': None, 'tcp443_owner': '', 'udp3478_busy': None,
              'public_ipv4': None}
    addresses = command(['ip', '-j', '-4', 'address', 'show', 'scope', 'global'])
    if addresses is not None:
        try:
            report['public_ipv4'] = any(ipaddress.ip_address(a['local']).is_global
                for interface in json.loads(addresses) for a in interface.get('addr_info', []))
        except (ValueError, KeyError, TypeError): pass
    tcp = command(['ss', '-H', '-tlpn', 'sport = :443'])
    if tcp is not None:
        report['tcp443_busy'] = bool(tcp.strip())
        report['tcp443_owner'] = ', '.join(sorted(set(re.findall(r'\("([\w.+-]{1,80})"', tcp))))
    udp = command(['ss', '-H', '-ulpn', 'sport = :3478'])
    if udp is not None: report['udp3478_busy'] = bool(udp.strip())

    version = command(['headscale', 'version'])
    if version is not None: report['headscale'] = True
    config_path = Path('/etc/headscale/config.yaml')
    docker = command(['docker', 'ps', '--format', '{{.ID}}\t{{.Image}}\t{{.Names}}'])
    containers = []
    for line in (docker or '').splitlines():
        parts = line.split('\t')
        if len(parts) == 3 and re.fullmatch(r'[a-f0-9]{12,64}', parts[0]):
            if parts[2] == 'headscale' or parts[1].split('/')[-1].split(':')[0] == 'headscale': containers.append(parts[0])
    if len(containers) == 1:
        report['headscale'] = True
        if version is None: version = command(['docker', 'exec', containers[0], 'headscale', 'version'])
        if not config_path.is_file():
            mounts = command(['docker', 'inspect', '--format', '{{json .Mounts}}', containers[0]])
            try:
                for mount in json.loads(mounts or '[]'):
                    if mount.get('Destination') == '/etc/headscale': config_path = Path(mount['Source']) / 'config.yaml'
                    elif mount.get('Destination') == '/etc/headscale/config.yaml': config_path = Path(mount['Source'])
            except (ValueError, KeyError, TypeError): pass
    if report['headscale'] is None:
        unit = command(['systemctl', 'show', 'headscale.service', '--property=LoadState', '--value'])
        if unit and unit.strip() == 'loaded': report['headscale'] = True
        elif unit and unit.strip() == 'not-found' and docker is not None: report['headscale'] = False
    if version:
        match = re.search(r'\bv?\d+\.\d+\.\d+(?:[-+][\w.]+)?\b', version)
        if match: report['version'] = match.group(0)
    try:
        with config_path.open(encoding='utf-8') as source: raw = source.read(131073)
        if len(raw) > 131072: raise ValueError('config size')
        config = read_config(raw)
        host = config.pop('probe_host', '')
        report['config'] = config
        stun = config.get('stun_listen_addr', '')
        port = int(stun.rsplit(':', 1)[-1]) if stun else 3478
        if not 1 <= port <= 65535: raise ValueError('invalid port')
        report['stun_port'] = port
        listeners = udp if port == 3478 else command(['ss', '-H', '-ulpn', 'sport = :' + str(port)])
        if listeners is not None: report['stun_listening'] = bool(listeners.strip())
        if config.get('enabled') is True and re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]{0,251}[a-zA-Z0-9])?', host):
            code = command(['curl', '--noproxy', '*', '--silent', '--max-time', '2',
                            '--output', '/dev/null', '--write-out', '%{http_code}',
                            '--resolve', host + ':443:127.0.0.1', 'https://' + host + '/derp/probe'], timeout=2.5)
            # Certificate validation is intentionally retained. No redirects/body.
            report['probe_code'] = int(code) if code and re.fullmatch(r'\d{3}', code) else 0
    except (OSError, ValueError, TypeError): pass
    return report


if __name__ == '__main__':
    print('VPN_DERP_BEGIN')
    try: print(json.dumps(collect()))
    except Exception: print('{"state":"unavailable"}')
    print('VPN_DERP_END')
