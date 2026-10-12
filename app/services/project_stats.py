"""Read-only detection of tracked projects on a server (TelegramOnly is listed separately).

The list is editable on the Projects settings page and stored in the user profile config.json.
"""
import math
import re

from .ui_preferences import _config_path, _read_config, _write_config

DEFAULT_PROJECTS = [
    {'name': 'BotCriptoM',
     'units': ['botcriptom', 'botcriptom-dash', 'botcriptom-stop',
               'botcriptom-dash-bridge', 'botcriptom-stop-bridge'],
     'containers': ['botcriptom', 'botcriptom-dash', 'botcriptom-stop', 'botcriptom-proxy']},
    {'name': 'Rust File Manager', 'units': ['rust-file-manager', 'rfm-internal-bridge'], 'containers': []},
    {'name': 'UGCTL (UDP gRPC COM Lite)',
     'units': ['ugctl-server', 'ugctl-api', 'ugctl-bu', 'ugctl-bz', 'ugctl-bf',
               'ugctl-ha', 'ugctl-remote-cli'], 'containers': []},
    {'name': 'Reticulum', 'units': ['ha-reticulum-bridge', 'rnsd', 'lxmd', 'reticulum', 'ha-rns-watchdog.timer'],
     'containers': ['ha_rns_bridge', 'reticulumpn', 'reticulum']},
    {'name': 'Dockhand', 'units': [], 'containers': ['dockhand']},
    {'name': 'Headscale / Headplane', 'units': ['headscale', 'headplane'], 'containers': ['headscale', 'headplane']},
]
CONFIG_KEY = 'tracked_projects'
MAX_PROJECTS = 30
MAX_ITEMS = 16
# Names go into a shell command line, so only systemd/Docker-safe characters are accepted.
_ITEM = re.compile(r'[A-Za-z0-9][A-Za-z0-9@._-]{0,63}')
_DOCKER_STATES = {'running': 'active', 'restarting': 'failed', 'dead': 'failed',
                  'exited': 'inactive', 'created': 'inactive', 'paused': 'inactive'}


class ProjectError(ValueError):
    pass


def unit_id(unit):
    """Timers and sockets keep their suffix; any other name is a .service unit."""
    return unit if unit.endswith(('.timer', '.socket')) else unit + '.service'


def _items(value, field):
    if isinstance(value, str):
        value = re.split(r'[\s,]+', value)
    if not isinstance(value, (list, tuple)):
        raise ProjectError(field)
    items = []
    for item in value:
        item = str(item).strip()
        if field == 'units' and item.endswith('.service'):
            item = item[:-len('.service')]
        if not item:
            continue
        if not _ITEM.fullmatch(item):
            raise ProjectError(field)
        if item not in items:
            items.append(item)
    if len(items) > MAX_ITEMS:
        raise ProjectError(field)
    return items


def clean_projects(projects):
    """Validated list; entries without a name, services or containers are dropped."""
    if not isinstance(projects, list):
        raise ProjectError('projects')
    result, keys = [], set()
    for project in projects:
        if not isinstance(project, dict):
            raise ProjectError('projects')
        name = ' '.join(str(project.get('name') or '').split())[:60]
        units = _items(project.get('units') or [], 'units')
        containers = _items(project.get('containers') or [], 'containers')
        if not name and not units and not containers:
            continue
        if not name or not (units or containers):
            raise ProjectError('incomplete')
        key = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_') or 'project'
        while key in keys:
            key += '_'
        keys.add(key)
        result.append({'key': key, 'name': name, 'units': units, 'containers': containers})
    if len(result) > MAX_PROJECTS:
        raise ProjectError('projects')
    return result


def load_projects(app=None):
    if app is None:
        from flask import current_app, has_app_context
        if not has_app_context():
            return clean_projects(DEFAULT_PROJECTS)
        app = current_app
    stored = _read_config(_config_path(app)).get(CONFIG_KEY)
    try:
        return clean_projects(stored) if stored is not None else clean_projects(DEFAULT_PROJECTS)
    except ProjectError:
        return clean_projects(DEFAULT_PROJECTS)


def save_projects(app, projects):
    """Raises ProjectError on invalid input; None restores the defaults."""
    path = _config_path(app)
    data = _read_config(path)
    if projects is None:
        data.pop(CONFIG_KEY, None)
    else:
        data[CONFIG_KEY] = [{k: p[k] for k in ('name', 'units', 'containers')} for p in clean_projects(projects)]
    return _write_config(path, data)


def build_command(projects):
    """Fixed unit/property allowlist; never reads Environment, command lines or user files.
    Docker is asked only for container names and states."""
    units = ' '.join(unit_id(unit) for p in projects for unit in p['units'])
    show = ('systemctl show --no-pager -p Id -p LoadState -p ActiveState '
            '-p MainPID -p ActiveEnterTimestampMonotonic -p CPUUsageNSec '
            '-p MemoryCurrent -p TasksCurrent -- ' + units + ' 2>/dev/null') if units else 'true'
    uptime = "awk '{print \"UP=\" $1}' /proc/uptime; "
    docker = ("; printf '\\nDOCKER\\n'; if command -v docker >/dev/null 2>&1; then "
              "docker ps -a --format '{{.Names}}|{{.State}}' 2>/dev/null && echo DOCKER_OK; "
              "else echo NO_DOCKER; fi") if any(p['containers'] for p in projects) else ''
    return ("printf 'SAMPLE\\n'; " + uptime + show + "; sleep 1; printf '\\nSAMPLE\\n'; "
            + uptime + show + docker)


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) and 0 <= result < 2**64 - 1 else None
    except (TypeError, ValueError):
        return None


def _samples(text):
    samples = []
    for chunk in text.split('SAMPLE\n')[1:]:
        records, block, uptime = {}, {}, None
        for line in (chunk.strip() + '\n\n').splitlines():
            if line.startswith('UP='):
                uptime = number(line[3:])
            elif '=' in line:
                key, value = line.split('=', 1)
                block[key] = value
            elif block:
                records[block.get('Id')] = block
                block = {}
        samples.append((uptime, records))
    return samples


def _containers(text, names):
    """None when Docker did not answer (e.g. no access), so containers stay unknown."""
    lines = ('\n' + text).split('\nDOCKER\n', 1)[1].splitlines() if '\nDOCKER\n' in '\n' + text else []
    if 'NO_DOCKER' in lines:
        return {}
    if 'DOCKER_OK' not in lines:
        return None
    states = {}
    for line in lines:
        name, _, state = line.strip().partition('|')
        if name in names and re.fullmatch(r'[a-z]+', state):
            states[name] = _DOCKER_STATES.get(state, 'unknown')
    return states


def parse_sample(text, projects):
    """Component rows for every tracked unit and container.

    Missing/permission-denied measurements remain unknown, not zero.
    """
    text = text or ''
    samples = _samples(text.split('\nDOCKER\n', 1)[0])
    before = samples[0] if len(samples) >= 2 else (None, {})
    after = samples[-1] if samples else (None, {})
    elapsed = after[0] - before[0] if None not in (before[0], after[0]) else 0
    names = {name for p in projects for name in p['containers']}
    docker = _containers(text, names) if samples else None
    rows = []
    for project in projects:
        for unit in project['units']:
            old, state = before[1].get(unit_id(unit), {}), after[1].get(unit_id(unit), {})
            status = ('not_installed' if state.get('LoadState') == 'not-found'
                      else state.get('ActiveState', 'unknown'))
            cpu = None
            a, b = number(old.get('CPUUsageNSec')), number(state.get('CPUUsageNSec'))
            same_run = (old.get('MainPID') == state.get('MainPID')
                        and old.get('ActiveEnterTimestampMonotonic') == state.get('ActiveEnterTimestampMonotonic')
                        and number(state.get('MainPID')) not in (None, 0))
            if status == 'active' and same_run and elapsed > 0 and a is not None and b is not None and b >= a:
                cpu = round((b - a) / (elapsed * 1e9) * 100, 1)
            rows.append(_row(project, unit_id(unit), 'unit', status, cpu,
                             number(state.get('MemoryCurrent')) if status == 'active' else None,
                             number(state.get('TasksCurrent')) if status == 'active' else None))
        for name in project['containers']:
            status = 'unknown' if docker is None else docker.get(name, 'not_installed')
            rows.append(_row(project, name, 'container', status, None, None, None))
    return rows


def _row(project, name, kind, status, cpu, memory, tasks):
    return {'name': name, 'display_name': name, 'kind': kind, 'group': 'project',
            'project': project['key'], 'project_name': project['name'],
            'control_component': None, 'status': status, 'cpu_percent': cpu,
            'memory_bytes': memory, 'tasks': tasks}


def summarize(rows, projects):
    """Projects found on the server, each with its installed components."""
    result = []
    for project in projects:
        own = [row for row in rows if row['project'] == project['key']]
        found = [row for row in own if row['status'] not in ('not_installed', 'unknown')]
        if not found:
            if own and all(row['status'] == 'unknown' for row in own):
                result.append({'key': project['key'], 'name': project['name'], 'state': 'unknown', 'components': []})
            continue
        active = sum(row['status'] == 'active' for row in found)
        state = 'running' if active == len(found) else 'partial' if active else 'stopped'
        result.append({'key': project['key'], 'name': project['name'], 'state': state, 'components': found})
    return result
