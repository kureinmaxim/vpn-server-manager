"""Sending-only Telegram bots on a node: no process of their own, a timer or another program sends.

Found by markers only (read-only, over the same SSH call as the Bots overview):
- systemd timers: the unit's script contains api.telegram.org or sendMessage, or its
  EnvironmentFile has TELEGRAM_BOT_TOKEN (grep -q, contents are never printed);
- Uptime Kuma: notifications whose config mentions telegram (id, name, active only);
- containers: names of TELEGRAM_* / *BOT_TOKEN variables (values are cut by the docker template);
- Docker stacks on TerraMaster TOS (no Docker API over SSH): the same variable names from
  /Volume*/docker/stacks/*/compose.yaml and .env, values are dropped on the node.

A bot is identified by its numeric ID, the part of the token before the colon, cut on the
server. Optionally getMe runs on the server and only .result.username comes back. The token
and chat_id never leave the node; sendMessage is never called.
"""
import re
from datetime import datetime, timezone

from .project_stats import _ITEM

CONFIG_KEY = 'bots_getme'
MAX_SENDERS = 40
# Whatever slips through is masked again here: bot123:ABC… and bare 123:ABC… tokens.
_TOKEN = re.compile(r'(?:bot)?[0-9]{3,}:[A-Za-z0-9_-]{20,}')
_BOT_ID = re.compile(r'[0-9]{1,20}')
# Bot usernames: up to 32 characters ending in «bot»; a token secret (35 characters) never fits.
_USERNAME = re.compile(r'[A-Za-z][A-Za-z0-9_]{1,28}[Bb][Oo][Tt]')
_VARIABLE = re.compile(r'TELEGRAM_[A-Z0-9_]*|[A-Z0-9_]*BOT_TOKEN')
_SCHEDULE = re.compile(r'On[A-Za-z]+=[^;|]{1,120}')
MARKERS = {'a': 'api', 's': 'send_message', 'e': 'env_token', 't': 'script_token', 'k': 'kuma_token'}

# POSIX sh: the login shell of a NAS may be ash or dash. Placeholders: __GETME__.
SCRIPT = r'''printf 'SENDERS\n'
GETME=__GETME__
tg() {
  out=''
  while IFS= read -r t; do
    i=${t%%:*}
    case "$i" in ''|*[!0-9]*) continue;; esac
    case "$t" in *:*) ;; *) continue;; esac
    case "$t" in *[!0-9A-Za-z:_-]*) continue;; esac
    u=''
    if [ "$GETME" = 1 ] && command -v curl >/dev/null 2>&1; then
      u=$(printf 'url = "https://api.telegram.org/bot%s/getMe"\n' "$t" | curl -s -m 4 -K - 2>/dev/null | head -c 4096 | grep -oE '"username":"[A-Za-z0-9_]{1,64}"' | head -n 1 | cut -d'"' -f4)
    fi
    out="$out${out:+,}$i:$u"
  done
  printf '%s' "$out"
}
ts() { case "$1" in ''|n/a) ;; @*) printf '%s' "${1#@}";; *) date -d "$1" +%s 2>/dev/null;; esac; }
sv() { systemctl show --timestamp=unix -p "$1" --value -- "$2" 2>/dev/null || systemctl show -p "$1" --value -- "$2" 2>/dev/null; }
if command -v systemctl >/dev/null 2>&1; then
  set -f
  for tm in $(systemctl list-units --all --type=timer --no-legend --plain --no-pager 2>/dev/null | awk '{print $1}' | grep -E '^[A-Za-z0-9@_.:-]+[.]timer$' | head -n 60); do
    u=$(systemctl show -p Unit --value -- "$tm" 2>/dev/null)
    case "$u" in ''|*[!A-Za-z0-9@_.:-]*) continue;; esac
    args=$(systemctl show -p ExecStart --value -- "$u" 2>/dev/null | sed -n 's/.*argv\[\]=\([^;]*\);.*/\1/p')
    m=''; ids=''
    case "$args" in *api.telegram.org*) m="${m}a";; esac
    for w in $args; do
      case "$w" in /*) ;; *) continue;; esac
      [ -f "$w" ] || continue
      grep -Iq 'api[.]telegram[.]org' "$w" 2>/dev/null && m="${m}a"
      grep -Iq 'sendMessage' "$w" 2>/dev/null && m="${m}s"
      grep -Iq 'kuma[.]db' "$w" 2>/dev/null && grep -Iq 'telegramBotToken' "$w" 2>/dev/null && m="${m}k"
      x=$(grep -IoE '[0-9]{6,}:[A-Za-z0-9_-]{30,}' "$w" 2>/dev/null | sort -u | head -n 3 | tg)
      [ -n "$x" ] && ids="$ids${ids:+,}$x" && m="${m}t"
    done
    for f in $(systemctl show -p EnvironmentFiles --value -- "$u" 2>/dev/null | sed 's/ (ignore_errors=[a-z]*)$//'); do
      f=${f#-}
      [ -f "$f" ] || continue
      grep -Eq '^[[:space:]]*(export[[:space:]]+)?TELEGRAM_BOT_TOKEN=' "$f" 2>/dev/null && m="${m}e"
      x=$(sed -nE "s/^[[:space:]]*(export[[:space:]]+)?[A-Z0-9_]*(BOT_TOKEN|TELEGRAM_TOKEN)=[\"']?([0-9]+:[A-Za-z0-9_-]+).*/\3/p" "$f" 2>/dev/null | sort -u | head -n 3 | tg)
      [ -n "$x" ] && ids="$ids${ids:+,}$x" && m="${m}e"
    done
    [ -n "$m" ] || continue
    sched=$(systemctl show -p TimersCalendar -p TimersMonotonic --value -- "$tm" 2>/dev/null | grep -oE 'On[A-Za-z]+=[^;]*' | sed 's/ *$//' | tr '\n' ';')
    printf 'X=timer|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n' "$tm" "$u" "$m" "$ids" "$(ts "$(sv NextElapseUSecRealtime "$tm")")" "$(ts "$(sv ExecMainStartTimestamp "$u")")" "$(ts "$(sv ExecMainExitTimestamp "$u")")" "$(systemctl show -p Result --value -- "$u" 2>/dev/null)" "$(systemctl show -p ExecMainStatus --value -- "$u" 2>/dev/null)" "$(systemctl show -p ActiveState --value -- "$u" 2>/dev/null)" "$sched"
  done
  set +f
fi
if [ -n "$D" ] && "$D" ps -q >/dev/null 2>&1; then
  for c in $("$D" ps -a --format '{{.Names}}|{{.Image}}' 2>/dev/null | awk -F'|' '$2 ~ /uptime-kuma/ {print $1}' | head -n 3); do
    src=$("$D" inspect -f '{{range .Mounts}}{{if eq .Destination "/app/data"}}{{.Source}}{{end}}{{end}}' -- "$c" 2>/dev/null)
    db="$src/kuma.db"
    if [ -z "$src" ] || [ ! -e "$db" ]; then echo "KUMA=$c|nodb"; continue; fi
    if [ ! -r "$db" ]; then echo "KUMA=$c|noaccess"; continue; fi
    if [ -f "$src/db-config.json" ] && ! grep -Eq '"type"[[:space:]]*:[[:space:]]*"sqlite"' "$src/db-config.json" 2>/dev/null; then echo "KUMA=$c|external"; continue; fi
    if ! command -v sqlite3 >/dev/null 2>&1; then echo "KUMA=$c|nosqlite"; continue; fi
    echo "KUMA=$c|ok"
    sqlite3 -readonly -separator '|' "$db" "select id, active from notification where config like '%telegram%' limit 20" 2>/dev/null | while IFS='|' read -r n a; do
      case "$n" in ''|*[!0-9]*) continue;; esac
      nm=$(sqlite3 -readonly "$db" "select replace(replace(name, '|', '/'), char(10), ' ') from notification where id = $n" 2>/dev/null | head -n 1)
      x=$(sqlite3 -readonly "$db" "select json_extract(config, '\$.telegramBotToken') from notification where id = $n" 2>/dev/null | tg)
      printf 'X=kuma|%s|%s|%s|%s|%s\n' "$c" "$n" "$a" "$x" "$nm"
    done
  done
  "$D" inspect -f '{{.Name}}|{{.State.Status}}|{{range .Config.Env}}{{index (split . "=") 0}},{{end}}' $("$D" ps -aq 2>/dev/null | head -n 100) 2>/dev/null | grep -E '[|,](TELEGRAM_[A-Z0-9_]*|[A-Z0-9_]*BOT_TOKEN),' | sed 's/^/E=/'
fi
n=0
for f in /Volume*/docker/stacks/*/compose.yaml /Volume*/docker/stacks/*/compose.yml /Volume*/docker/stacks/*/docker-compose.yaml /Volume*/docker/stacks/*/docker-compose.yml /Volume*/docker/stacks/*/.env; do
  [ -e "$f" ] || continue
  n=$((n + 1)); s=${f%/*}; s=${s##*/}
  if [ -r "$f" ]; then
    v=$(sed -nE 's/^[[:space:]]*(-[[:space:]]*)?(export[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*[=:].*/\3/p' "$f" 2>/dev/null | grep -E '^(TELEGRAM_[A-Z0-9_]*|[A-Z0-9_]*BOT_TOKEN)$' | sort -u | tr '\n' ',')
    [ -n "$v" ] && printf 'F=%s|%s\n' "$s" "$v"
  else
    printf 'F=%s|!\n' "$s"
  fi
done
echo "STACK_FILES=$n"
'''


def build_section(getme=True):
    """Shell section appended to the Bots script; expects $D (docker binary or empty) to be set."""
    return SCRIPT.replace('__GETME__', '1' if getme else '0')


def mask(value):
    return _TOKEN.sub('bot***', str(value or ''))


def _bots(value):
    """'id:username,id:' → [{'id', 'username'}] without duplicates."""
    result = []
    for item in (value or '').split(','):
        bot_id, _, username = item.partition(':')
        if not _BOT_ID.fullmatch(bot_id) or len(username) > 32:
            continue
        username = username if _USERNAME.fullmatch(username) else None
        if all(b['id'] != bot_id for b in result):
            result.append({'id': bot_id, 'username': username})
        elif username:
            next(b for b in result if b['id'] == bot_id)['username'] = username
    return result


def _iso(value):
    try:
        epoch = int(value)
    except (TypeError, ValueError):
        return None
    if epoch <= 0:
        return None
    try:
        return datetime.fromtimestamp(epoch, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    except (OverflowError, OSError, ValueError):
        return None


def _last_result(started, result, status, active):
    if active in ('activating', 'reloading'):
        return 'running'
    if not started:
        return 'never'
    return 'ok' if result in ('success', '') and status in ('0', '') else 'failed'


def _timer(parts):
    if len(parts) != 11:
        return None
    timer, unit, marks, ids, upcoming, started, exited, result, status, active, schedule = parts
    if not (_ITEM.fullmatch(timer) and _ITEM.fullmatch(unit)):
        return None
    markers = [MARKERS[mark] for mark in dict.fromkeys(marks) if mark in MARKERS]
    if not markers:
        return None
    started_at = _iso(started)
    return {'kind': 'timer', 'name': unit, 'timer': timer, 'markers': markers, 'bots': _bots(ids),
            'token_source': 'kuma' if 'kuma_token' in markers else 'env' if 'env_token' in markers
            else 'script' if 'script_token' in markers else None,
            'schedule': [mask(item) for item in _SCHEDULE.findall(schedule)][:4],
            'next': _iso(upcoming), 'last_run': started_at, 'last_exit': _iso(exited),
            'result': _last_result(started_at, result, status, active),
            'exit_status': int(status) if status.isdigit() else None}


def _kuma(parts):
    if len(parts) < 5:
        return None
    container, notification, active, ids = parts[:4]
    name = '|'.join(parts[4:])
    if not (_ITEM.fullmatch(container) and notification.isdigit()):
        return None
    return {'kind': 'kuma', 'name': mask(' '.join(name.split()))[:80], 'container': container,
            'notification_id': int(notification), 'active': active == '1', 'bots': _bots(ids)}


def _container(line, skip):
    name, _, rest = line.partition('|')
    status, _, variables = rest.partition('|')
    name = name.lstrip('/')
    if not _ITEM.fullmatch(name) or name in skip:
        return None
    names = [v for v in dict.fromkeys(variables.split(',')) if _VARIABLE.fullmatch(v)]
    if not names:
        return None
    return {'kind': 'container', 'name': name, 'state': status if _ITEM.fullmatch(status) else 'unknown',
            'variables': names[:6], 'bots': []}


def _stacks(lines):
    """Stack files checked, stacks with bot variables (as sender rows) and unreadable stacks."""
    files, rows, closed = 0, {}, []
    for line in lines:
        if line.startswith('STACK_FILES=') and line[12:].isdigit():
            files = int(line[12:])
        elif line.startswith('F='):
            stack, _, variables = line[2:].partition('|')
            if not _ITEM.fullmatch(stack):
                continue
            if variables == '!':
                if stack not in closed:
                    closed.append(stack)
                continue
            names = [v for v in variables.split(',') if _VARIABLE.fullmatch(v)]
            if names:
                row = rows.setdefault(stack, {'kind': 'stack', 'name': stack, 'variables': [], 'bots': []})
                row['variables'] = list(dict.fromkeys(row['variables'] + names))[:6]
    return {'files': files, 'unreadable': closed[:10]}, list(rows.values())


def parse(lines, skip_containers=()):
    """{'senders': [...], 'kuma': [...], 'stacks': {...}} from the SENDERS section lines."""
    senders, kuma = [], []
    for line in lines:
        if line.startswith('KUMA='):
            container, _, state = line[5:].partition('|')
            if _ITEM.fullmatch(container) and state in ('ok', 'nodb', 'noaccess', 'external', 'nosqlite'):
                kuma.append({'container': container, 'state': state})
        elif line.startswith('X=timer|'):
            row = _timer(line[len('X=timer|'):].split('|'))
            if row:
                senders.append(row)
        elif line.startswith('X=kuma|'):
            row = _kuma(line[len('X=kuma|'):].split('|'))
            if row:
                senders.append(row)
    kuma_containers = {row['container'] for row in kuma}
    for line in lines:
        if line.startswith('E='):
            row = _container(line[2:], set(skip_containers) | kuma_containers)
            if row:
                senders.append(row)
    # A script that takes its token from Uptime Kuma's base sends as the Kuma bot of this node.
    kuma_bots = []
    for row in senders:
        if row['kind'] == 'kuma':
            kuma_bots += [bot for bot in row['bots'] if all(b['id'] != bot['id'] for b in kuma_bots)]
    for row in senders:
        if row['kind'] == 'timer' and row['token_source'] == 'kuma' and not row['bots']:
            row['bots'] = [dict(bot) for bot in kuma_bots]
    stacks, stack_rows = _stacks(lines)
    senders += stack_rows
    return {'senders': senders[:MAX_SENDERS], 'kuma': kuma, 'stacks': stacks}
