import json
import re

import pytest

from app.services.bot_stats import (DEFAULT_BOTS, BotError, build_command, clean_bots, load_bots, parse,
                                    save_bots)

BOTS = clean_bots(DEFAULT_BOTS)
NOW = 1_800_000_000
UPTIME = 100_000.0
BOOT = NOW - UPTIME


def unit(name, active='active', sub='running', type_='simple', result='success', restarts=0,
         memory='52428800', entered=50_000_000_000, inactive=0, load='loaded'):
    return '\n'.join([
        f'Id={name}', f'LoadState={load}', f'ActiveState={active}', f'SubState={sub}', f'Type={type_}',
        f'Result={result}', f'NRestarts={restarts}', f'MemoryCurrent={memory}',
        f'ActiveEnterTimestampMonotonic={entered}', f'InactiveEnterTimestampMonotonic={inactive}']) + '\n\n'


def output(units='', docker='NO_DOCKER', suspects='', health='HEALTH_OK\nH=telegramonly=ok', node_extra=''):
    return '\n'.join([
        'NODE', 'OS_ID=debian', 'OS_NAME=Debian GNU/Linux', 'SYSTEMD=1', f'NOW={NOW}', f'UP={UPTIME}',
        node_extra, '', 'UNITS', units, '', 'SUSPECTS', suspects, 'DOCKER', docker,
        'HEALTH', health, 'END'])


ULTRAHOST = output(
    unit('telegramonly.service', restarts=2)
    + unit('telegramonly-maintenance.service', active='inactive', sub='dead', type_='oneshot',
           memory='[not set]', entered=0, inactive=90_000_000_000)
    + ''.join(unit(name, active='inactive', sub='dead', load='not-found', memory='[not set]', entered=0)
              for name in ('botcriptom.service', 'botcriptom-dash.service', 'botcriptom-stop.service',
                           'botcriptom-dash-bridge.service', 'botcriptom-stop-bridge.service',
                           'botcriptom-fleet-drain.service', 'monitoring-weekly.service'))
    # Not requested by the command; must never be parsed or returned.
    + 'Environment=BOT_TOKEN=123456:SECRET\nEnvironmentFile=/opt/TelegramOnly/.env\n')


def test_telegramonly_running_with_health_and_helper_block():
    result = parse(ULTRAHOST, BOTS)
    assert {k: result['node'][k] for k in ('systemd', 'docker', 'tos', 'processes')} == {
        'systemd': True, 'docker': 'absent', 'tos': False, 'processes': False}
    [bot] = result['bots']
    assert (bot['name'], bot['state'], bot['health']) == ('TelegramOnly', 'running', 'ok')
    [component] = bot['components']
    assert component['restarts'] == 2 and component['memory_bytes'] == 52428800
    [helper] = result['helpers']
    assert helper['owner'] == 'TelegramOnly maintenance' and helper['state'] == 'idle'
    assert helper['result'] == 'success' and helper['since'] and helper['memory_bytes'] is None


def test_since_is_boot_plus_monotonic():
    [bot] = parse(ULTRAHOST, BOTS)['bots']
    from datetime import datetime, timezone
    expected = datetime.fromtimestamp(BOOT + 50_000, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    assert bot['components'][0]['since'] == expected


def test_environment_never_reaches_the_response():
    text = json.dumps(parse(ULTRAHOST, BOTS))
    assert 'SECRET' not in text and 'Environment' not in text and '.env' not in text


@pytest.mark.parametrize('active,sub,result,expected', [
    ('active', 'running', 'success', 'running'),
    ('failed', 'failed', 'exit-code', 'failed'),
    ('activating', 'auto-restart', 'exit-code', 'restarting'),
    ('inactive', 'dead', 'success', 'stopped'),
])
def test_unit_states(active, sub, result, expected):
    text = output(unit('telegramonly.service', active=active, sub=sub, result=result))
    assert parse(text, BOTS)['bots'][0]['state'] == expected


def test_failed_oneshot_is_reported_in_helpers_not_as_bot_state():
    missing = ''.join(unit(name, active='inactive', sub='dead', load='not-found', entered=0)
                      for name in ('botcriptom-dash.service', 'botcriptom-stop.service',
                                   'botcriptom-dash-bridge.service', 'botcriptom-stop-bridge.service'))
    text = output(unit('botcriptom.service') + missing
                  + unit('botcriptom-fleet-drain.service', active='failed', sub='failed', type_='oneshot',
                         result='exit-code', entered=0, inactive=1_000_000))
    result = parse(text, BOTS)
    bot = next(b for b in result['bots'] if b['name'] == 'BotCriptoM')
    assert bot['state'] == 'running' and [c['name'] for c in bot['components']] == ['botcriptom.service']
    [helper] = result['helpers']
    assert (helper['owner'], helper['state'], helper['result']) == ('BotCriptoM', 'failed', 'exit-code')


def test_partial_bot():
    text = output(unit('botcriptom.service') + unit('botcriptom-dash.service', active='inactive', sub='dead'))
    bot = next(b for b in parse(text, BOTS)['bots'] if b['name'] == 'BotCriptoM')
    assert bot['state'] == 'partial'


DOCKER_OK = '\n'.join([
    'C=telegram-helper-lite|running', 'C=uptime-kuma|running', 'C=my-telegram-bot|exited', 'C=', 'DOCKER_OK',
    'I=/telegram-helper-lite|running|2026-10-20T08:00:00.123456789Z|3|healthy|0'])


def test_docker_container_with_health_and_suspects():
    result = parse(output(docker=DOCKER_OK, suspects='S=news-bot.service\nS=telegramonly.service'), BOTS)
    bot = next(b for b in result['bots'] if b['name'] == 'telegram-helper-lite')
    [component] = bot['components']
    assert component == {'kind': 'container', 'name': 'telegram-helper-lite', 'state': 'running',
                         'since': '2026-10-20T08:00:00Z', 'restarts': 3, 'memory_bytes': None,
                         'oneshot': False, 'result': 'healthy'}
    assert result['suspects'] == [{'kind': 'unit', 'name': 'news-bot.service'},
                                  {'kind': 'container', 'name': 'my-telegram-bot'}]


def test_certbot_and_robot_are_not_suspects():
    result = parse(output(suspects='S=certbot.service\nS=robot-vacuum.service\nS=my_bot.service'), BOTS)
    assert result['suspects'] == [{'kind': 'unit', 'name': 'my_bot.service'}]


@pytest.mark.parametrize('status,health,code,expected', [
    ('running', 'unhealthy', '0', 'failed'), ('restarting', '', '1', 'restarting'),
    ('exited', '', '137', 'failed'), ('exited', '', '0', 'stopped')])
def test_container_states(status, health, code, expected):
    docker = f'C=telegram-helper-lite|{status}\nDOCKER_OK\nI=/telegram-helper-lite|{status}|0001-01-01T00:00:00Z|0|{health}|{code}'
    bot = next(b for b in parse(output(docker=docker), BOTS)['bots'] if b['name'] == 'telegram-helper-lite')
    assert bot['state'] == expected and bot['components'][0]['since'] is None


def test_tos_without_docker_api_is_explicit_not_an_error():
    text = output(docker='DOCKER_FAIL', node_extra='TOS_APPS=1').replace('SYSTEMD=1\n', '')
    result = parse(text, BOTS)
    assert {k: result['node'][k] for k in ('systemd', 'docker', 'tos', 'processes')} == {
        'systemd': False, 'docker': 'unavailable', 'tos': True, 'processes': False}
    assert result['bots'] == []


def test_tos_docker_path_containers_visible():
    result = parse(output(docker=DOCKER_OK, node_extra='TOS_APPS=1'), BOTS)
    assert result['node']['tos'] and result['node']['docker'] == 'ok'
    assert any(b['name'] == 'telegram-helper-lite' for b in result['bots'])


def test_processes_counted():
    bots = clean_bots([{'name': 'Manual bot', 'processes': ['mybot']}])
    text = output(health='') + '\nPROC\nP=mybot=2\nPROC_OK\nEND'
    [bot] = parse(text, bots)['bots']
    assert bot['state'] == 'running' and bot['components'][0]['count'] == 2


def test_command_is_read_only_and_never_reads_secrets():
    # The senders section has its own rules (tests/test_services/test_bot_senders.py).
    command = build_command(BOTS).split("printf 'SENDERS")[0]
    assert not re.search(r'systemctl\s+(start|stop|restart|reload|enable|disable|kill)\b', command)
    assert not re.search(r'docker"?\s+(start|stop|restart|exec|kill|rm|logs)\b', command)
    for forbidden in ('Environment', 'Config.Env', 'environ', 'journalctl', 'cat ', '.env', 'sudo'):
        assert forbidden not in command
    assert 'systemctl show --no-pager -p Id' in command
    assert "-- telegramonly.service botcriptom.service" in command
    assert "curl -s -m 3 http://127.0.0.1:8000/health" in command and 'grep -qw -- healthy' in command
    assert '/Volume*/@apps/DockerEngine/dockerd/bin/docker' in command


@pytest.mark.parametrize('bot,error', [
    ({'name': 'Evil', 'units': ['x; reboot']}, 'units'),
    ({'name': 'Evil', 'containers': ['$(id)']}, 'containers'),
    ({'name': 'Evil', 'processes': ['a-very-long-process-name']}, 'processes'),
    ({'name': 'Evil', 'units': ['ok'], 'health_url': 'http://example.com/health', 'health_word': 'ok'}, 'health_url'),
    ({'name': 'Evil', 'units': ['ok'], 'health_url': 'http://127.0.0.1:8000/h?x=`id`', 'health_word': 'ok'}, 'health_url'),
    ({'name': 'Evil', 'units': ['ok'], 'health_url': 'http://127.0.0.1:99999/', 'health_word': 'ok'}, 'health_url'),
    ({'name': 'Evil', 'units': ['ok'], 'health_url': 'http://127.0.0.1:8000/health', 'health_word': "a'b"}, 'health_word'),
    ({'name': 'No parts'}, 'incomplete'),
])
def test_catalog_validation_rejects_shell_unsafe_names(bot, error):
    with pytest.raises(BotError) as exc:
        clean_bots([bot])
    assert str(exc.value) == error


def test_catalog_normalises_and_saves(app):
    saved = save_bots(app, [{'name': ' My  bot ', 'units': 'mybot.service, mybot-worker', 'containers': '',
                             'health_url': 'http://127.0.0.1:9000/health', 'health_word': 'ok', 'service': False}])
    assert saved
    [bot] = load_bots(app)
    assert (bot['name'], bot['units'], bot['health_url']) == ('My bot', ['mybot', 'mybot-worker'],
                                                              'http://127.0.0.1:9000/health')
    save_bots(app, None)
    assert [b['name'] for b in load_bots(app)] == [b['name'] for b in BOTS]
