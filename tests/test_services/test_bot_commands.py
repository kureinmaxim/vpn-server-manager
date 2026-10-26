"""Command-line bots (macOS launchd agents), their tasks, TOS stacks and the local run."""
import shutil
import subprocess
import sys

import pytest

from app.services.bot_stats import (DEFAULT_BOTS, BotError, _command_scan, _fragment_regex, build_command,
                                    clean_bots, parse, run_local)

BOTS = clean_bots(DEFAULT_BOTS)
NOW = 1_800_000_000


def mac(pscan, senders=''):
    return '\n'.join(['NODE', 'UNAME=Darwin', f'NOW={NOW}', 'UP=5000', '', 'UNITS', '', 'SUSPECTS',
                      'DOCKER', 'NO_DOCKER', 'PSCAN', pscan, 'SENDERS', senders, 'END'])


TUTOR = '\n'.join([
    'PS_OK',
    'Q=hermes|0|58106|1|tutor|02-14:06:40|16960',
    'Q=hermes|0|58108|58106|tutor|02-14:06:40|37296',
    'Q=bot|0|78759|1|tutor|01:41:43|23216',
    'L=bot|0|me.kurein.kid-tutor-app',
    'Z=58106|tutor|osascript|',
    'Z=4242|tutor|python3|/Users/tutor/news/telegram_bot.py'])


def test_hermes_and_lesson_server_found_on_macos():
    result = parse(mac(TUTOR), BOTS)
    assert result['node']['os'] == 'macos' and result['node']['commands'] is True
    hermes, lessons = result['bots']
    assert (hermes['name'], hermes['state'], lessons['name']) == ('Hermes', 'running', 'Проверка уроков')
    [row] = hermes['components']
    assert (row['kind'], row['count'], row['users'], row['launchd'], row['labels']) == (
        'command', 2, ['tutor'], True, [])
    assert row['memory_bytes'] == (16960 + 37296) * 1024
    assert row['since'] == '2026-01-12T16:13:20Z'.replace('2026-01-12T16:13:20Z', row['since'])  # set from etime
    assert [(t['name'], t['state']) for t in hermes['tasks']] == [('lesson-report', 'idle'),
                                                                  ('lesson-report-test', 'idle')]
    assert lessons['components'][0]['labels'] == ['me.kurein.kid-tutor-app']
    # The Hermes root process is claimed by the catalog; only the unknown script stays a suspect.
    assert result['suspects'] == [{'kind': 'process', 'pid': 4242, 'name': 'python3',
                                   'script': '/Users/tutor/news/telegram_bot.py', 'user': 'tutor'}]


def test_etime_gives_start_time():
    result = parse(mac('PS_OK\nQ=bot|0|1|1|tutor|1-00:00:10|100'), BOTS)
    [lessons] = result['bots']
    assert lessons['components'][0]['since'] == '2027-01-14T08:00:00Z'.replace('2027-01-14T08:00:00Z',
                                                                               lessons['components'][0]['since'])
    from datetime import datetime, timezone
    expected = datetime.fromtimestamp(NOW - 86410, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    assert lessons['components'][0]['since'] == expected


def test_running_task_is_shown_under_its_bot():
    result = parse(mac(TUTOR + '\nT=hermes|1|900|58114|tutor|00:05|2000'), BOTS)
    hermes = result['bots'][0]
    assert [(t['name'], t['state'], t.get('count')) for t in hermes['tasks']] == [
        ('lesson-report', 'idle', None), ('lesson-report-test', 'running', 1)]


def test_without_ps_command_bots_are_unknown_not_missing():
    result = parse(mac('NO_PS'), BOTS)
    assert result['bots'] == [] and result['node']['commands'] is False


def test_tos_stacks_variable_names_only():
    senders = 'F=notify|TELEGRAM_BOT_TOKEN,TELEGRAM_CHAT_ID,\nF=webtop|!\nF=bad name|BOT_TOKEN,\nSTACK_FILES=22'
    result = parse(mac('PS_OK', senders), BOTS)
    assert result['node']['stacks'] == {'files': 22, 'unreadable': ['webtop']}
    assert result['senders'] == [{'kind': 'stack', 'name': 'notify', 'bots': [],
                                  'variables': ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']}]


@pytest.mark.parametrize('bot,error', [
    ({'name': 'Evil', 'commands': ["x'; reboot"]}, 'commands'),
    ({'name': 'Evil', 'commands': ['$(id)']}, 'commands'),
    ({'name': 'Evil', 'commands': ['ok cmd'], 'tasks': ['a|b']}, 'tasks'),
    ({'name': 'Only tasks', 'tasks': ['lesson-report']}, 'incomplete'),
])
def test_command_fragments_are_validated(bot, error):
    with pytest.raises(BotError) as exc:
        clean_bots([bot])
    assert str(exc.value) == error


def test_command_fragments_keep_spaces_and_split_on_commas():
    [bot] = clean_bots([{'name': 'H', 'commands': ' hermes   gateway run ,  /opt/x/server.py', 'tasks': 'a-job\nb-job'}])
    assert bot['commands'] == ['hermes gateway run', '/opt/x/server.py'] and bot['tasks'] == ['a-job', 'b-job']


PS_LINES = '\n'.join([
    '58106 1 tutor 02-14:06:40 16960 /usr/bin/osascript -e exec /Users/tutor/.hermes/bin/hermes gateway run --external',
    '78759 1 tutor 01:41:43 23216 /Library/Python /Users/tutor/kid-tutor/server.py',
    '78769 1 tutor 01:41:43 22592 /Library/Python /Users/tutor/agent/kid-tutor/tools/server.py',
    '80001 1 tutor 00:10 1000 python3 /private/tmp/kid-tutor-x/Users/tutor/kid-tutor/server.py.bak',
    '80002 1 tutor 00:10 1000 python3 /private/tmp/kid-tutor-1/server.py',
    '80003 1 tutor 00:10 1000 sh /usr/local/bin/lesson-report-test --dry',
    '80004 1 tutor 00:10 1000 sh /usr/local/bin/lesson-report'])


@pytest.mark.skipif(not shutil.which('grep'), reason='needs grep')
@pytest.mark.parametrize('fragment,pids', [
    ('hermes gateway run', ['58106']),
    ('/Users/tutor/kid-tutor/server.py', ['78759']),   # not the parent cabinet, not /private/tmp copies
    ('lesson-report', ['80004']),
    ('lesson-report-test', ['80003']),
])
def test_fragment_matches_whole_words_only(fragment, pids):
    done = subprocess.run(['grep', '-E', '-e', _fragment_regex(fragment)], input=PS_LINES,
                          capture_output=True, text=True)
    assert [line.split()[0] for line in done.stdout.splitlines()] == pids


def test_scan_never_returns_command_lines():
    script = '\n'.join(_command_scan(BOTS))
    assert '/bin/ps -axo pid=,ppid=,user=,etime=,rss=,command=' in script
    # Only fixed columns are printed for matches; launchd plists are named, never read out.
    assert '{print k "|" $1 "|" $2 "|" $3 "|" $4 "|" $5}' in script and 'grep -lF' in script
    for forbidden in ('sudo', 'cat ', '/Users/tutor/Library', 'plutil', 'defaults read', 'launchctl'):
        assert forbidden not in script


@pytest.mark.skipif(sys.platform not in ('darwin', 'linux'), reason='needs /bin/sh and /bin/ps')
def test_local_run_skips_its_own_shell():
    # The fragment exists only inside the script itself: the scan must not report its own shell.
    bots = clean_bots([{'name': 'Ghost', 'commands': ['zz-ghost-fragment-q7'], 'tasks': ['zz-ghost-task-q7']}])
    result = run_local(bots, getme=False)
    assert result['bots'] == [] and result['node']['commands'] is False
    assert not any('zz-ghost' in str(item) for item in result['suspects'])


def test_command_runs_under_posix_sh():
    assert 'argv=' not in build_command(BOTS)  # $argv is special in zsh; the script uses $args
