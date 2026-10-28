import json
import re
import shutil
import subprocess

import pytest

from app.services import bot_senders
from app.services.bot_stats import DEFAULT_BOTS, build_command, clean_bots, load_getme, parse, save_getme

BOTS = clean_bots(DEFAULT_BOTS)
# Ненастоящий токен той же формы; собран из частей, чтобы сканер секретов не принимал его за утечку
TOKEN = '123456789:' + 'AA' + 'TestOnly' * 4


def output(senders):
    return '\n'.join(['NODE', 'SYSTEMD=1', 'NOW=1800000000', 'UP=1000', '', 'UNITS', '', 'SUSPECTS', 'DOCKER',
                      'C=telegram-helper-lite|running', 'DOCKER_OK', 'SENDERS', senders, 'END'])


WATCHDOG = ('X=timer|homelab-watchdog.timer|homelab-watchdog.service|aseee|8867590267:kurein_homelab_alerts_bot|'
            '|1800000000|1800000001|success|0|inactive|OnUnitActiveUSec=10min;OnBootUSec=2min;')
WEEKLY = ('X=timer|monitoring-weekly.timer|monitoring-weekly.service|ask||1800600000|||success|0|inactive|'
          'OnCalendar=Mon *-*-* 10:00:00 Europe/Moscow;')
KUMA = 'KUMA=uptime-kuma|ok\nX=kuma|uptime-kuma|1|1|8867590267:kurein_homelab_alerts_bot|Telegram | bot'


def test_timer_with_env_token_is_a_sender():
    [row] = parse(output(WATCHDOG), BOTS)['senders']
    assert row == {
        'kind': 'timer', 'name': 'homelab-watchdog.service', 'timer': 'homelab-watchdog.timer',
        'markers': ['api', 'send_message', 'env_token'],
        'bots': [{'id': '8867590267', 'username': 'kurein_homelab_alerts_bot'}], 'token_source': 'env',
        'schedule': ['OnUnitActiveUSec=10min', 'OnBootUSec=2min'], 'next': None,
        'last_run': '2027-01-15T08:00:00Z', 'last_exit': '2027-01-15T08:00:01Z', 'result': 'ok', 'exit_status': 0}


def test_kuma_notification_and_weekly_script_share_the_kuma_bot():
    result = parse(output(WEEKLY + '\n' + KUMA), BOTS)
    weekly, kuma = result['senders']
    assert weekly['token_source'] == 'kuma' and weekly['result'] == 'never' and weekly['next']
    assert weekly['bots'] == kuma['bots'] == [{'id': '8867590267', 'username': 'kurein_homelab_alerts_bot'}]
    assert (kuma['name'], kuma['active'], kuma['notification_id']) == ('Telegram | bot', True, 1)
    assert result['node']['kuma'] == [{'container': 'uptime-kuma', 'state': 'ok'}]


@pytest.mark.parametrize('result,status,active,expected', [
    ('exit-code', '1', 'failed', 'failed'), ('success', '0', 'activating', 'running')])
def test_last_run_result(result, status, active, expected):
    line = f'X=timer|a.timer|a.service|s||||1800000000|1800000001|{result}|{status}|{active}|'
    [row] = parse(output(line.replace('||||', '|||', 1)), BOTS)['senders']
    assert row['result'] == expected


def test_containers_only_variable_names_and_catalog_containers_skipped():
    lines = ('E=/notify|running|PATH,TELEGRAM_BOT_TOKEN,TELEGRAM_CHAT_ID,\n'
             'E=/telegram-helper-lite|running|BOT_TOKEN,\nE=/plain|running|PATH,HOME,')
    [row] = parse(output(lines), BOTS)['senders']
    assert row == {'kind': 'container', 'name': 'notify', 'state': 'running',
                   'variables': ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'], 'bots': []}


def test_tokens_and_garbage_never_reach_the_response():
    lines = '\n'.join([
        f'X=kuma|uptime-kuma|2|0|{TOKEN}|alerts bot{TOKEN}',                # token instead of an ID
        f'X=timer|x.timer|x.service|a|{TOKEN}|||||||OnCalendar=daily {TOKEN}',  # wrong field count
        'X=timer|bad;name|x.service|a||||||0||',
        'X=timer|y.timer|y.service|zz||||||0||',                             # no Telegram markers
        'KUMA=uptime-kuma|weird'])
    result = parse(output(lines), BOTS)
    text = json.dumps(result)
    assert 'AAHdq' not in text and '123456789:' not in text
    kuma = result['senders'][0]
    assert kuma['bots'] == [] and kuma['name'] == 'alerts bot***'
    assert all(row['bots'] == [] for row in result['senders'])
    assert result['node']['kuma'] == []


def test_metadata_probe_never_reads_token_sources():
    for getme in (False, True):
        script = build_command(BOTS, getme=getme)
        for forbidden in ('SENDERS', 'Config.Env', 'Environment', 'getMe', '.env', '/bin/ps', '.plist'):
            assert forbidden not in script


@pytest.mark.skipif(not shutil.which('sh'), reason='needs a POSIX shell')
def test_tg_cuts_the_id_and_keeps_the_token_out_of_argv(tmp_path):
    tg = re.search(r'tg\(\) \{.*?\n\}\n', bot_senders.SCRIPT, re.S).group(0)
    curl = tmp_path / 'curl'
    curl.write_text('#!/bin/sh\necho "$@" >> "$LOG"\ncat >> "$LOG.stdin"\n'
                    'printf \'{"ok":true,"result":{"id":1,"is_bot":true,"username":"demo_bot"}}\'\n')
    curl.chmod(0o755)
    env = {'PATH': f'{tmp_path}:/usr/bin:/bin', 'LOG': str(tmp_path / 'argv')}
    script = tg + f'GETME=1\nprintf "%s\\n" "{TOKEN}" "not-a-token" "12:bad token" | tg\n'
    done = subprocess.run(['sh', '-c', script], env=env, capture_output=True, text=True, timeout=10)
    assert done.stdout == '123456789:demo_bot'
    assert TOKEN not in (tmp_path / 'argv').read_text()
    assert TOKEN in (tmp_path / 'argv.stdin').read_text()
    without = subprocess.run(['sh', '-c', tg + f'GETME=0\nprintf "%s\\n" "{TOKEN}" | tg\n'],
                             env=env, capture_output=True, text=True, timeout=10)
    assert without.stdout == '123456789:'


def test_getme_setting_cannot_enable_secret_scanning(app):
    assert load_getme(app) is False
    save_getme(app, False)
    assert load_getme(app) is False
    save_getme(app, True)
    assert load_getme(app) is False
