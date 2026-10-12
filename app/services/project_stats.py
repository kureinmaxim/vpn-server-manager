"""Read-only detection of the owner's own projects on a server (TelegramOnly is listed separately)."""
import math
import re

PROJECTS = [
    {'key': 'botcriptom', 'name': 'BotCriptoM',
     'units': ['botcriptom', 'botcriptom-dash', 'botcriptom-stop',
               'botcriptom-dash-bridge', 'botcriptom-stop-bridge'],
     'containers': ['botcriptom', 'botcriptom-dash', 'botcriptom-stop', 'botcriptom-proxy']},
    {'key': 'rust_file_manager', 'name': 'Rust File Manager',
     'units': ['rust-file-manager', 'rfm-internal-bridge'], 'containers': []},
    {'key': 'ugctl', 'name': 'UGCTL (UDP gRPC COM Lite)',
     'units': ['ugctl-server', 'ugctl-api', 'ugctl-bu', 'ugctl-bz', 'ugctl-bf',
               'ugctl-ha', 'ugctl-remote-cli'], 'containers': []},
    {'key': 'apiai', 'name': 'ApiAigRPC', 'units': ['apiai-backend'], 'containers': []},
    {'key': 'aping', 'name': 'ApiNgRPC', 'units': ['aping-server'], 'containers': []},
    {'key': 'apix', 'name': 'ApiXgRPC', 'units': ['apix-server'], 'containers': []},
    {'key': 'telegramhelper', 'name': 'TelegramHelper', 'units': ['telegramhelper'], 'containers': []},
    {'key': 'pdf3md', 'name': 'PDF3MD', 'units': [], 'containers': ['pdf3md-backend', 'pdf3md-frontend']},
]
UNITS = [unit + '.service' for project in PROJECTS for unit in project['units']]
CONTAINERS = {name for project in PROJECTS for name in project['containers']}
_DOCKER_STATES = {'running': 'active', 'restarting': 'failed', 'dead': 'failed',
                  'exited': 'inactive', 'created': 'inactive', 'paused': 'inactive'}

# Fixed unit/property allowlist; never read Environment, command lines or user files.
# Docker is asked only for container names and states.
_SHOW = ('systemctl show --no-pager -p Id -p LoadState -p ActiveState '
         '-p MainPID -p ActiveEnterTimestampMonotonic -p CPUUsageNSec '
         '-p MemoryCurrent -p TasksCurrent -- ' + ' '.join(UNITS) + ' 2>/dev/null')
_UPTIME = "awk '{print \"UP=\" $1}' /proc/uptime; "
COMMAND = ("printf 'SAMPLE\\n'; " + _UPTIME + _SHOW + "; sleep 1; printf '\\nSAMPLE\\n'; " + _UPTIME + _SHOW
           + "; printf '\\nDOCKER\\n'; if command -v docker >/dev/null 2>&1; then "
           "docker ps -a --format '{{.Names}}|{{.State}}' 2>/dev/null && echo DOCKER_OK; "
           "else echo NO_DOCKER; fi")


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


def _containers(text):
    """None when Docker did not answer (e.g. no access), so containers stay unknown."""
    lines = ('\n' + text).split('\nDOCKER\n', 1)[1].splitlines() if '\nDOCKER\n' in '\n' + text else []
    if 'NO_DOCKER' in lines:
        return {}
    if 'DOCKER_OK' not in lines:
        return None
    states = {}
    for line in lines:
        name, _, state = line.strip().partition('|')
        if name in CONTAINERS and re.fullmatch(r'[a-z]+', state):
            states[name] = _DOCKER_STATES.get(state, 'unknown')
    return states


def parse_sample(text):
    """Component rows for every catalogued unit and container.

    Missing/permission-denied measurements remain unknown, not zero.
    """
    text = text or ''
    samples = _samples(text.split('\nDOCKER\n', 1)[0])
    before = samples[0] if len(samples) >= 2 else (None, {})
    after = samples[-1] if samples else (None, {})
    elapsed = after[0] - before[0] if None not in (before[0], after[0]) else 0
    docker = _containers(text) if samples else None
    rows = []
    for project in PROJECTS:
        for unit in project['units']:
            old, state = before[1].get(unit + '.service', {}), after[1].get(unit + '.service', {})
            status = ('not_installed' if state.get('LoadState') == 'not-found'
                      else state.get('ActiveState', 'unknown'))
            cpu = None
            a, b = number(old.get('CPUUsageNSec')), number(state.get('CPUUsageNSec'))
            same_run = (old.get('MainPID') == state.get('MainPID')
                        and old.get('ActiveEnterTimestampMonotonic') == state.get('ActiveEnterTimestampMonotonic')
                        and number(state.get('MainPID')) not in (None, 0))
            if status == 'active' and same_run and elapsed > 0 and a is not None and b is not None and b >= a:
                cpu = round((b - a) / (elapsed * 1e9) * 100, 1)
            rows.append(_row(project, unit + '.service', 'unit', status, cpu,
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


def summarize(rows):
    """Projects found on the server, each with its installed components."""
    projects = []
    for project in PROJECTS:
        own = [row for row in rows if row['project'] == project['key']]
        found = [row for row in own if row['status'] not in ('not_installed', 'unknown')]
        if not found:
            if own and all(row['status'] == 'unknown' for row in own):
                projects.append({'key': project['key'], 'name': project['name'], 'state': 'unknown', 'components': []})
            continue
        active = sum(row['status'] == 'active' for row in found)
        state = 'running' if active == len(found) else 'partial' if active else 'stopped'
        projects.append({'key': project['key'], 'name': project['name'], 'state': state, 'components': found})
    return projects
