"""Read-only state of Telegram bots on a node (VPS, NAS or PC card).

The catalog is editable on the Bots settings page and stored in the user profile config.json.
Bots with a process: only fixed systemd properties, Docker state fields, process-name counts and
a local health word are read, never Environment, Config.Env values, /proc/*/environ, configs or logs.
Sending-only bots (timers, Uptime Kuma) are found by markers in bot_senders: there the token
stays on the node and only the bot ID and @username come back.
"""
import re
import shlex
from datetime import datetime, timezone

from . import bot_senders
from .project_stats import _ITEM, _PROCESS, ProjectError, number, unit_id
from .ui_preferences import _config_path, _read_config, _write_config

DEFAULT_BOTS = [
    {'name': 'TelegramOnly', 'units': ['telegramonly'],
     'health_url': 'http://127.0.0.1:8000/health', 'health_word': 'healthy'},
    {'name': 'BotCriptoM',
     'units': ['botcriptom', 'botcriptom-dash', 'botcriptom-stop', 'botcriptom-dash-bridge',
               'botcriptom-stop-bridge', 'botcriptom-fleet-drain']},
    {'name': 'telegram-helper-lite', 'containers': ['telegram-helper-lite']},
    # macOS mesh nodes: no systemd or Docker, recognised by the command line (launchd agents).
    {'name': 'Hermes', 'commands': ['hermes gateway run'], 'tasks': ['lesson-report', 'lesson-report-test']},
    {'name': 'Проверка уроков', 'commands': ['/Users/tutor/kid-tutor/server.py']},
    {'name': 'TelegramOnly maintenance', 'units': ['telegramonly-maintenance'], 'service': True},
    {'name': 'Weekly monitoring report', 'units': ['monitoring-weekly'], 'service': True},
]
CONFIG_KEY = 'tracked_bots'
MAX_BOTS = 30
MAX_ITEMS = 16
MAX_SUSPECTS = 20
FIELDS = ('units', 'containers', 'processes', 'commands')
# Command-line fragments (ps command column): matched as a whole word, never sent back.
_COMMAND = re.compile(r'[A-Za-z0-9/][A-Za-z0-9 /._@:+-]{2,99}')
_WORD_EDGE = '[^A-Za-z0-9_-]'
# Health checks stay on the node itself: loopback HTTP only, path without query or shell characters.
_HEALTH_URL = re.compile(r'http://127\.0\.0\.1:([0-9]{1,5})(/[A-Za-z0-9/_.-]{0,64})?')
_HEALTH_WORD = re.compile(r'[A-Za-z0-9_-]{1,32}')
# «bot» as a word or a name prefix (news-bot, botcriptom), not inside certbot or robot.
_SUSPECT = re.compile(r'(?:^|[^a-z0-9])bot|telegram', re.I)
_INSPECT = '{{.Name}}|{{.State.Status}}|{{.State.StartedAt}}|{{.RestartCount}}|' \
           '{{if .State.Health}}{{.State.Health.Status}}{{end}}|{{.State.ExitCode}}'
SHOW_PROPERTIES = ('Id', 'LoadState', 'ActiveState', 'SubState', 'Type', 'Result', 'NRestarts',
                   'MemoryCurrent', 'ActiveEnterTimestampMonotonic', 'InactiveEnterTimestampMonotonic')


class BotError(ProjectError):
    pass


def _items(value, field):
    if isinstance(value, str):
        # Command fragments may contain spaces: only commas and new lines separate them.
        value = re.split(r'[,\n]+' if field in ('commands', 'tasks') else r'[\s,]+', value)
    if not isinstance(value, (list, tuple)):
        raise BotError(field)
    items = []
    for item in value:
        item = ' '.join(str(item).split()) if field in ('commands', 'tasks') else str(item).strip()
        if field == 'units' and item.endswith('.service'):
            item = item[:-len('.service')]
        if not item:
            continue
        pattern = {'processes': _PROCESS, 'commands': _COMMAND, 'tasks': _COMMAND}.get(field, _ITEM)
        if not pattern.fullmatch(item):
            raise BotError(field)
        if item not in items:
            items.append(item)
    if len(items) > MAX_ITEMS:
        raise BotError(field)
    return items


def _health(bot):
    url = str(bot.get('health_url') or '').strip()
    word = str(bot.get('health_word') or '').strip()
    if not url and not word:
        return '', ''
    match = _HEALTH_URL.fullmatch(url)
    if not match or not 1 <= int(match.group(1)) <= 65535:
        raise BotError('health_url')
    if not _HEALTH_WORD.fullmatch(word):
        raise BotError('health_word')
    return url, word


def clean_bots(bots):
    """Validated catalog; empty rows are dropped."""
    if not isinstance(bots, list):
        raise BotError('bots')
    result, keys = [], set()
    for bot in bots:
        if not isinstance(bot, dict):
            raise BotError('bots')
        name = ' '.join(str(bot.get('name') or '').split())[:60]
        items = {field: _items(bot.get(field) or [], field) for field in FIELDS}
        tasks = _items(bot.get('tasks') or [], 'tasks')
        url, word = _health(bot)
        if not name and not any(items.values()) and not url:
            continue
        if not name or not any(items.values()):
            raise BotError('incomplete')
        key = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_') or 'bot'
        while key in keys:
            key += '_'
        keys.add(key)
        service = bot.get('service') in (True, 'true', '1', 'on', 'service')
        result.append({'key': key, 'name': name, **items, 'tasks': tasks, 'health_url': url, 'health_word': word,
                       'service': service})
    if len(result) > MAX_BOTS:
        raise BotError('bots')
    return result


def load_bots(app=None):
    if app is None:
        from flask import current_app, has_app_context
        if not has_app_context():
            return clean_bots(DEFAULT_BOTS)
        app = current_app
    stored = _read_config(_config_path(app)).get(CONFIG_KEY)
    try:
        return clean_bots(DEFAULT_BOTS if stored is None else stored)
    except BotError:
        return clean_bots(DEFAULT_BOTS)


def save_bots(app, bots):
    """Raises BotError on invalid input; None restores the defaults."""
    path = _config_path(app)
    data = _read_config(path)
    if bots is None:
        data.pop(CONFIG_KEY, None)
    else:
        data[CONFIG_KEY] = [{k: b[k] for k in ('name',) + FIELDS + ('tasks', 'health_url', 'health_word', 'service')}
                            for b in clean_bots(bots)]
    return _write_config(path, data)


def load_getme(app):
    """Token discovery is disabled in the metadata-only security baseline."""
    return False


def save_getme(app, enabled):
    path = _config_path(app)
    data = _read_config(path)
    if enabled:
        data.pop(bot_senders.CONFIG_KEY, None)
    else:
        data[bot_senders.CONFIG_KEY] = False
    return _write_config(path, data)


def run_local(bots, getme=False, timeout=40):
    """The same read-only script on this computer (the PC the app runs on), without SSH."""
    import subprocess
    done = subprocess.run(['/bin/sh', '-c', build_command(bots, getme)], capture_output=True, timeout=timeout,
                          stdin=subprocess.DEVNULL, check=False)
    output = done.stdout[:262144].decode('utf-8', errors='replace')
    if 'END' not in output.splitlines():
        raise ValueError('incomplete bots snapshot')
    return parse(output, bots)


def build_command(bots, getme=False):
    """One read-only script: fixed systemctl properties, Docker state fields, pgrep counts,
    and a loopback health word matched on the node; no token or command-line scanning."""
    units = ' '.join(unit_id(unit) for b in bots for unit in b['units'])
    containers = ' '.join(name for b in bots for name in b['containers'])
    script = [
        'PATH="$PATH:/usr/local/sbin:/usr/local/bin:/usr/sbin:/sbin"',
        "printf 'NODE\\n'",
        "grep -E '^(ID|NAME)=' /etc/os-release 2>/dev/null | head -2 | tr -d '\"' | sed 's/^/OS_/'",
        'ls -d /Volume*/@apps >/dev/null 2>&1 && echo TOS_APPS=1',
        'command -v systemctl >/dev/null 2>&1 && echo SYSTEMD=1',
        'echo "UNAME=$(uname -s 2>/dev/null)"',
        'date +NOW=%s',
        "awk '{print \"UP=\" $1}' /proc/uptime 2>/dev/null",
        "printf '\\nUNITS\\n'",
    ]
    if units:
        script.append('systemctl show --no-pager ' + ' '.join('-p ' + p for p in SHOW_PROPERTIES)
                      + ' -- ' + units + ' 2>/dev/null')
    script += [
        "printf '\\nSUSPECTS\\n'",
        "systemctl list-units --all --type=service --no-legend --plain '*bot*' '*telegram*' 2>/dev/null"
        " | awk '{print \"S=\" $1}' | head -40",
        "printf 'DOCKER\\n'",
        'D=$(command -v docker 2>/dev/null)',
        'if [ -z "$D" ]; then for c in /Volume*/@apps/DockerEngine/dockerd/bin/docker; do'
        ' [ -x "$c" ] && D="$c" && break; done; fi',
        'if [ -z "$D" ]; then echo NO_DOCKER;'
        " elif OUT=$(\"$D\" ps -a --format '{{.Names}}|{{.State}}' 2>/dev/null); then"
        " printf '%s\\n' \"$OUT\" | head -200 | sed 's/^/C=/'; echo DOCKER_OK;"
        + ((" \"$D\" inspect -f '" + _INSPECT + "' -- " + containers + " 2>/dev/null | sed 's/^/I=/';")
           if containers else '')
        + ' else echo DOCKER_FAIL; fi',
    ]
    names = ' '.join(shlex.quote(name) for b in bots for name in b['processes'])
    if names:
        script += ["printf 'PROC\\n'",
                   'if command -v pgrep >/dev/null 2>&1; then for p in ' + names
                   + '; do printf \'P=%s=%s\\n\' "$p" "$(pgrep -x -- "$p" | wc -l | tr -d \' \')"; done;'
                   ' echo PROC_OK; else echo NO_PGREP; fi']
    # Command lines, launchd plists and token sources are deliberately not read.
    checks = [b for b in bots if b['health_url']]
    if checks:
        script += ["printf 'HEALTH\\n'",
                   'if command -v curl >/dev/null 2>&1; then '
                   + ' '.join("if curl -s --noproxy '*' -m 3 %s 2>/dev/null | head -c 65536 | grep -qw -- %s;"
                              " then echo H=%s=ok; else echo H=%s=fail; fi;"
                              % (shlex.quote(b['health_url']), shlex.quote(b['health_word']), b['key'], b['key'])
                              for b in checks)
                   + ' echo HEALTH_OK; else echo NO_CURL; fi']
    # Sending-only Bot API identities have no observable process state.
    script.append("printf 'END\\n'")
    return '\n'.join(script)


def _fragment_regex(fragment):
    escaped = re.sub(r'([.+])', r'\\\1', fragment)
    return '(^|%s)%s($|%s)' % (_WORD_EDGE, escaped, _WORD_EDGE)


def _command_scan(bots):
    """/bin/ps once; for each catalog fragment only pid, ppid, user, etime and rss come back,
    never the command line. The script's shell, all its ancestors (sh -c, the login shell, the app
    or terminal that started it) and its children are skipped: their argv may hold the fragments.
    Without systemd (macOS) processes that look like bots are listed by program and script name only."""
    lines = ["printf 'PSCAN\\n'",
             'if PS=$(/bin/ps -axo pid=,ppid=,user=,etime=,rss=,command= 2>/dev/null); then echo PS_OK',
             'PS=$(printf \'%s\\n\' "$PS" | awk -v s="$$" \'{ pp[$1] = $2; row[NR] = $0; id[NR] = $1; up[NR] = $2 }'
             ' END { a = s; while (a != "" && a != 0 && !(a in mine)) { mine[a] = 1; a = pp[a] }'
             ' for (i = 1; i <= NR; i++) if (!(id[i] in mine) && up[i] != s) print row[i] }\')',
             'psm() { printf \'%s\\n\' "$PS" | grep -E -e "$2"'
             ' | awk -v k="$1" \'{print k "|" $1 "|" $2 "|" $3 "|" $4 "|" $5}\' | head -n 20; }']
    for bot in bots:
        for kind, field in (('Q', 'commands'), ('T', 'tasks')):
            for index, fragment in enumerate(bot[field]):
                lines.append('psm %s %s' % (shlex.quote('%s=%s|%d' % (kind, bot['key'], index)),
                                            shlex.quote(_fragment_regex(fragment))))
        for index, fragment in enumerate(bot['commands']):
            # launchd label: the plist that names the program (file name only; plists may hold secrets).
            lines.append('[ "$(uname -s)" = Darwin ] && grep -lF -e %s /Library/LaunchDaemons/*.plist'
                         ' /Library/LaunchAgents/*.plist "$HOME"/Library/LaunchAgents/*.plist 2>/dev/null'
                         ' | head -n 3 | sed -e \'s|.*/||\' -e \'s|[.]plist$||\' -e \'s|^|L=%s\\|%d\\||\''
                         % (shlex.quote(fragment), bot['key'], index))
    lines += ['if ! command -v systemctl >/dev/null 2>&1; then printf \'%s\\n\' "$PS"'
              ' | awk \'{ n=$6; sub(/.*\\//, "", n); sc=""; for (i = 7; i <= NF; i++) if ($i ~ /^\\/.*[.](py|js|mjs|ts|sh|rb)$/) { sc=$i; break }'
              ' if ($6 ~ /[.]app\\/Contents\\// && sc == "") next;'
              ' if (tolower(n " " sc) ~ /(^|[^a-z0-9])bot|telegram/) print "Z=" $1 "|" $3 "|" n "|" sc }\' | head -n 20; fi',
              'fi']
    return lines


def _etime(value):
    """ps etime [[dd-]hh:]mm:ss → seconds."""
    match = re.fullmatch(r'(?:(\d+)-)?(?:(\d+):)?(\d+):(\d+)', value or '')
    if not match:
        return None
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return ((days * 24 + hours) * 60 + minutes) * 60 + seconds


def _scan(lines):
    """{(kind, key, index): [process rows]}, {(key, index): [labels]}, suspects; None when ps failed."""
    if 'PS_OK' not in lines:
        return None, {}, []
    matches, labels, suspects = {}, {}, []
    for line in lines:
        if line[:2] in ('Q=', 'T=', 'L='):
            parts = line[2:].split('|')
            if len(parts) < 3 or not parts[1].isdigit():
                continue
            key = (parts[0], int(parts[1]))
            if line[0] == 'L':
                if _ITEM.fullmatch(parts[2]):
                    labels.setdefault(key, []).append(parts[2])
            elif len(parts) == 7 and parts[2].isdigit() and parts[3].isdigit():
                matches.setdefault((line[0],) + key, []).append({
                    'pid': int(parts[2]), 'ppid': int(parts[3]), 'user': parts[4] if _PROCESS_USER.fullmatch(parts[4]) else '',
                    'age': _etime(parts[5]), 'rss': number(parts[6])})
        elif line.startswith('Z='):
            parts = line[2:].split('|')
            if len(parts) == 4 and parts[0].isdigit():
                name = bot_senders.mask(parts[2])[:40]
                script = bot_senders.mask(parts[3])[:160] if parts[3].startswith('/') else ''
                if name:
                    suspects.append({'kind': 'process', 'pid': int(parts[0]), 'name': name, 'script': script,
                                     'user': parts[1] if _PROCESS_USER.fullmatch(parts[1]) else ''})
    return matches, labels, suspects


_PROCESS_USER = re.compile(r'[A-Za-z0-9_.-]{1,32}')


def _command_row(name, rows, now, labels, kind='command'):
    oldest = max((row['age'] for row in rows if row['age'] is not None), default=None)
    memory = int(sum(row['rss'] or 0 for row in rows) * 1024) or None
    row = _component(kind, name, 'running', since=_iso(now - oldest) if now is not None and oldest is not None else None,
                     memory=memory)
    row.update(count=len(rows), users=sorted({r['user'] for r in rows if r['user']}),
               launchd=any(r['ppid'] == 1 for r in rows), labels=labels)
    return row


_SECTIONS = ('NODE', 'UNITS', 'SUSPECTS', 'DOCKER', 'PROC', 'PSCAN', 'HEALTH', 'SENDERS', 'END')


def _sections(text):
    result, current = {}, None
    for line in (text or '').splitlines():
        if line in _SECTIONS:
            current = line
            result.setdefault(current, [])
        elif current:
            result[current].append(line)
    return result


def _pairs(lines, prefix):
    return [line[len(prefix):] for line in lines if line.startswith(prefix)]


def _units(lines):
    records, block = {}, {}
    for line in lines + ['']:
        if '=' in line:
            key, value = line.split('=', 1)
            block[key] = value
        elif block:
            if block.get('Id'):
                records[block['Id']] = block
            block = {}
    return records


def _iso(epoch):
    try:
        return datetime.fromtimestamp(round(epoch), timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    except (OverflowError, OSError, ValueError, TypeError):
        return None


def _since(boot, monotonic):
    """Wall-clock time from a *TimestampMonotonic property (0 means never)."""
    value = number(monotonic)
    if boot is None or not value:
        return None
    return _iso(boot + value / 1e6)


def _unit_state(record):
    if not record:
        return 'unknown'
    if record.get('LoadState') == 'not-found':
        return 'not_installed'
    active, sub = record.get('ActiveState'), record.get('SubState')
    if record.get('Type') == 'oneshot':
        if active == 'failed' or record.get('Result') not in (None, '', 'success'):
            return 'failed'
        return 'running' if active == 'activating' else 'idle'
    if active == 'failed':
        return 'failed'
    if active in ('activating', 'reloading') or sub == 'auto-restart':
        return 'restarting'
    if active == 'active':
        return 'running'
    if active in ('inactive', 'deactivating'):
        return 'stopped'
    return 'unknown'


def _container_state(status, health, exit_code):
    if status == 'running':
        return 'failed' if health == 'unhealthy' else 'running'
    if status == 'restarting':
        return 'restarting'
    if status == 'dead' or (status == 'exited' and exit_code not in ('', '0')):
        return 'failed'
    if status in ('exited', 'created', 'paused'):
        return 'stopped'
    return 'unknown'


_DOCKER_PS = {'running': 'running', 'restarting': 'restarting', 'dead': 'failed',
              'exited': 'stopped', 'created': 'stopped', 'paused': 'stopped'}


def _docker(lines):
    """(state, {name: ps state}, {name: inspect fields}); state is ok, absent or unavailable."""
    if 'NO_DOCKER' in lines:
        return 'absent', {}, {}
    if 'DOCKER_OK' not in lines:
        return 'unavailable', {}, {}
    listed = {}
    for line in _pairs(lines, 'C='):
        name, _, state = line.partition('|')
        if _ITEM.fullmatch(name):
            listed[name] = state
    inspected = {}
    for line in _pairs(lines, 'I='):
        parts = line.split('|')
        if len(parts) == 6:
            name = parts[0].lstrip('/')
            inspected[name] = dict(zip(('status', 'started', 'restarts', 'health', 'exit_code'), parts[1:]))
    return 'ok', listed, inspected


def _started(value):
    """Docker State.StartedAt (RFC 3339 with nanoseconds); the zero time means never started."""
    match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', value or '')
    if not match or match.group(1).startswith('0001'):
        return None
    return match.group(1) + 'Z' if (value or '').endswith('Z') else None


def _component(kind, name, state, since=None, restarts=None, memory=None, oneshot=False, result=None):
    return {'kind': kind, 'name': name, 'state': state, 'since': since, 'restarts': restarts,
            'memory_bytes': memory, 'oneshot': oneshot, 'result': result}


def _aggregate(components):
    # Unmeasured components keep their own "no data" mark but do not decide the bot state.
    states = [row['state'] for row in components if row['state'] != 'unknown']
    if not states:
        return 'unknown'
    if all(state == 'running' for state in states):
        return 'running'
    if 'failed' in states:
        return 'failed'
    if 'restarting' in states:
        return 'restarting'
    if 'running' in states:
        return 'partial'
    return 'stopped'


def parse(text, bots):
    """Bots found on the node, oneshot helpers and names that look like bots.

    Components that could not be measured stay unknown; nothing from Environment is parsed.
    """
    sections = _sections(text)
    node_lines = sections.get('NODE', [])
    values = dict(line.split('=', 1) for line in node_lines if '=' in line)
    os_text = (values.get('OS_ID', '') + ' ' + values.get('OS_NAME', '')).lower()
    tos = values.get('TOS_APPS') == '1' or 'tos' in os_text.split() or 'terramaster' in os_text
    systemd = values.get('SYSTEMD') == '1' and 'UNITS' in sections
    now, uptime = number(values.get('NOW')), number(values.get('UP'))
    boot = now - uptime if None not in (now, uptime) else None
    records = _units(sections.get('UNITS', [])) if systemd else {}
    docker, listed, inspected = _docker(sections.get('DOCKER', []))
    proc_lines = sections.get('PROC')
    counts = None
    if proc_lines is not None and 'PROC_OK' in proc_lines:
        counts = {}
        for line in _pairs(proc_lines, 'P='):
            name, _, count = line.rpartition('=')
            if count.isdigit():
                counts[name] = int(count)
    scan, labels, process_suspects = _scan(sections.get('PSCAN', [])) if 'PSCAN' in sections else (None, {}, [])
    health_lines = sections.get('HEALTH', [])
    health = {}
    if 'HEALTH_OK' in health_lines:
        for line in _pairs(health_lines, 'H='):
            key, _, result = line.rpartition('=')
            if result in ('ok', 'fail'):
                health[key] = result

    found, helpers, claimed_pids = [], [], set()
    for bot in bots:
        rows = []
        for unit in bot['units']:
            record = records.get(unit_id(unit)) or {}
            state = _unit_state(record) if systemd else 'unknown'
            if state == 'not_installed':
                continue
            oneshot = record.get('Type') == 'oneshot'
            alive = state in ('running', 'restarting')
            since = None
            if alive or oneshot:
                since = _since(boot, record.get('InactiveEnterTimestampMonotonic' if oneshot and not alive
                                                else 'ActiveEnterTimestampMonotonic'))
            rows.append(_component(
                'unit', unit_id(unit), state, since=since, restarts=number(record.get('NRestarts')),
                memory=number(record.get('MemoryCurrent')) if alive and not oneshot else None,
                oneshot=oneshot or bot['service'], result=record.get('Result') if oneshot else None))
        for name in bot['containers']:
            if docker != 'ok':
                rows.append(_component('container', name, 'unknown'))
                continue
            if name not in listed:
                continue
            info = inspected.get(name)
            if info:
                state = _container_state(info['status'], info['health'], info['exit_code'])
                rows.append(_component('container', name, state,
                                       since=_started(info['started']) if state in ('running', 'restarting') else None,
                                       restarts=number(info['restarts']),
                                       result=info['health'] or None))
            else:
                rows.append(_component('container', name, _DOCKER_PS.get(listed[name], 'unknown')))
        for name in bot['processes']:
            count = None if counts is None else counts.get(name)
            if count == 0:
                continue
            row = _component('process', name, 'unknown' if count is None else 'running')
            row['count'] = count
            rows.append(row)
        matched_pids = set()
        for index, fragment in enumerate(bot['commands']):
            if scan is None:
                rows.append(_component('command', fragment, 'unknown'))
                continue
            found_rows = scan.get(('Q', bot['key'], index))
            if found_rows:
                matched_pids.update(r['pid'] for r in found_rows)
                rows.append(_command_row(fragment, found_rows, now, labels.get((bot['key'], index), [])))
        if not any(row['state'] != 'unknown' for row in rows):
            continue
        claimed_pids.update(matched_pids)
        for row in rows:
            if row['oneshot']:
                helpers.append(dict(row, owner=bot['name']))
        main = [row for row in rows if not row['oneshot']]
        if not main:
            continue
        state = _aggregate(main)
        tasks = []
        for index, task in enumerate(bot['tasks']):
            task_rows = None if scan is None else scan.get(('T', bot['key'], index))
            if task_rows:
                claimed_pids.update(r['pid'] for r in task_rows)
                tasks.append(_command_row(task, task_rows, now, [], kind='task'))
            else:
                tasks.append(_component('task', task, 'unknown' if scan is None else 'idle'))
        found.append({'key': bot['key'], 'name': bot['name'], 'state': state,
                      'health': health.get(bot['key']) if bot['health_url'] else None,
                      'components': main, 'tasks': tasks})

    known_units = {unit_id(u) for b in bots for u in b['units']}
    known_containers = {c for b in bots for c in b['containers']}
    suspects = []
    for unit in _pairs(sections.get('SUSPECTS', []), 'S='):
        if unit not in known_units and _ITEM.fullmatch(unit) and _SUSPECT.search(unit):
            suspects.append({'kind': 'unit', 'name': unit})
    for name in listed:
        if name not in known_containers and _SUSPECT.search(name):
            suspects.append({'kind': 'container', 'name': name})
    for row in process_suspects:
        if row['pid'] not in claimed_pids and all(s.get('pid') != row['pid'] for s in suspects):
            suspects.append(row)
    senders = bot_senders.parse(sections.get('SENDERS', []), known_containers)
    uname = values.get('UNAME', '')
    return {'node': {'systemd': systemd, 'docker': docker, 'tos': tos, 'processes': counts is not None,
                     'os': 'macos' if uname == 'Darwin' else 'linux' if uname == 'Linux' else 'other',
                     'commands': scan is not None, 'kuma': senders['kuma'], 'stacks': senders['stacks']},
            'bots': found, 'helpers': helpers, 'suspects': suspects[:MAX_SUSPECTS],
            'senders': senders['senders']}
