"""Wire format and allowlist for the optional read-only SSH DERP probe."""
import json
from pathlib import Path
import shlex


def probe_command():
    script = Path(__file__).with_name('derp_probe.py').read_text(encoding='utf-8')
    # No installation and no sudo. Missing dependencies leave DERP unknown.
    return 'sh -c ' + shlex.quote('command -v timeout >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1 && timeout 12 python3 -c ' + shlex.quote(script))


def parse_remote_derp(output):
    try:
        if len(output) > 65536: raise ValueError('oversize')
        raw = output.split('VPN_DERP_BEGIN\n', 1)[1].split('\nVPN_DERP_END', 1)[0]
        data = json.loads(raw)
        if data.get('state') != 'ready': return {'state': 'unavailable'}
        result = {'state': 'ready'}
        for key in ('headscale', 'stun_listening', 'tcp443_busy', 'udp3478_busy', 'public_ipv4'):
            result[key] = data.get(key) if type(data.get(key)) is bool else None
        for key in ('probe_code', 'stun_port'):
            result[key] = data.get(key) if type(data.get(key)) is int else None
        for key in ('version', 'tcp443_owner'):
            result[key] = str(data.get(key) or '')[:160]
        config = data.get('config')
        result['config'] = None
        if isinstance(config, dict):
            result['config'] = {}
            for key in ('enabled', 'verify_clients', 'has_urls', 'public_map'):
                result['config'][key] = config.get(key) if type(config.get(key)) is bool else None
            result['config']['region_id'] = config.get('region_id') if type(config.get('region_id')) is int else None
            for key in ('region_code', 'region_name', 'stun_listen_addr', 'ipv4'):
                result['config'][key] = str(config.get(key) or '')[:160]
        return result
    except (IndexError, ValueError, TypeError, AttributeError):
        return {'state': 'unavailable'}
