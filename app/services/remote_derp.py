"""Wire format and allowlist for the optional read-only SSH DERP probe."""
import json
from datetime import datetime, timezone
from pathlib import Path
import shlex

DERP_ROLE = 'derp'
DERP_NAME = 'Свой DERP'


def derp_display_name():
    try:
        from flask_babel import gettext as _
        return _('Свой DERP')
    except Exception:
        return DERP_NAME


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


def role_summary(report):
    """Projects-window row when Headscale has an embedded DERP server enabled."""
    if not isinstance(report, dict) or report.get('state') != 'ready':
        return None
    cfg = report.get('config') if isinstance(report.get('config'), dict) else None
    if not cfg or cfg.get('enabled') is not True:
        return None
    code, stun = report.get('probe_code'), report.get('stun_listening')
    healthy = code == 200 and stun is True
    failed = code not in (None, 200) or stun is False
    state = 'running' if healthy else 'stopped' if failed else 'partial'
    region = (cfg.get('region_code') or 'derp')[:80]
    port = report.get('stun_port') if type(report.get('stun_port')) is int else 3478
    stun_status = 'active' if stun is True else 'inactive' if stun is False else 'unknown'
    name = derp_display_name()
    check = 'healthy' if healthy else 'error' if failed else 'unconfigured'
    return {
        'key': DERP_ROLE, 'name': name, 'detected': True, 'state': state,
        'components': [
            {'name': 'derp:' + region, 'kind': 'unit', 'status': 'active' if not failed else 'failed',
             'optional': False},
            {'name': 'stun:' + str(port), 'kind': 'unit', 'status': stun_status, 'optional': False},
        ],
        'discovery': 'detected', 'source': 'ssh',
        'last_check': {'state': check, 'checked_at': datetime.now(timezone.utc).isoformat(),
                       'source': 'ssh', 'stale': False},
    }


def discovery_rows(client):
    try:
        _, stdout, _ = client.exec_command(probe_command(), timeout=14)
        try:
            report = parse_remote_derp(stdout.read(65537).decode('utf-8', 'replace'))
        finally:
            stdout.channel.close()
        summary = role_summary(report)
    except Exception:
        return []
    if not summary:
        return []
    return [dict(name=summary['name'], display_name=summary['name'], kind='role', group='project',
                 project=summary['key'], project_name=summary['name'], status='unknown',
                 control_component=None, role_summary=summary)]
