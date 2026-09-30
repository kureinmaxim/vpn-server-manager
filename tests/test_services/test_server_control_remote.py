import json
import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace
from app.services import server_control_remote as remote


def fixture_run(argv):
    if argv[0:2] == ['systemctl', 'list-unit-files']:
        return 0, 'xray.service enabled\ntelegramonly.service disabled\n'
    if argv[0:2] == ['systemctl', 'show']:
        unit = argv[2]
        return 0, f'Id={unit}\nLoadState=loaded\nActiveState=active\nSubState=running\nFragmentPath=/etc/systemd/system/{unit}'
    if argv[0:2] == ['docker', 'ps']:
        return 0, json.dumps({'ID': 'a'*64, 'Names': 'telegram-helper-lite', 'State': 'exited', 'Labels': ''})
    raise AssertionError(argv)


def test_mixed_runtime_and_stopped_bot(monkeypatch):
    monkeypatch.setattr(remote, 'run', fixture_run)
    monkeypatch.setattr(remote.os, 'geteuid', lambda: 0, raising=False)
    data = remote.discover()
    components = {c['key']: c['instances'] for c in data['components']}
    assert components['vless'][0]['runtime'] == 'systemd'
    assert len(components['bot']) == 2
    assert components['bot'][1]['state'] == 'exited'
    assert not components['tuic']


def test_no_bot_no_container_required(monkeypatch):
    monkeypatch.setattr(remote, 'run', lambda argv: (127, '') if argv[0] == 'docker' else fixture_run(argv))
    monkeypatch.setattr(remote.os, 'geteuid', lambda: 0, raising=False)
    plan = remote.plan(dict(component='vless', instance='xray.service', runtime='systemd', action='restart'))
    assert plan['target']['id'] == 'xray.service'


@pytest.mark.parametrize('instance', ['ssh.service', 'xray.service; reboot', '--all', ''])
def test_unknown_target_never_executed(monkeypatch, instance):
    monkeypatch.setattr(remote, 'run', fixture_run)
    monkeypatch.setattr(remote.os, 'geteuid', lambda: 0, raising=False)
    with pytest.raises(ValueError):
        remote.plan(dict(component='vless', instance=instance, runtime='systemd', action='restart'))


def test_plan_hash_changes_with_state(monkeypatch):
    monkeypatch.setattr(remote, 'run', fixture_run)
    monkeypatch.setattr(remote.os, 'geteuid', lambda: 0, raising=False)
    body = dict(component='vless', instance='xray.service', runtime='systemd', action='restart')
    before = remote.plan(body)['plan_hash']
    monkeypatch.setattr(remote, 'run', lambda argv: (lambda result: (result[0], result[1].replace('ActiveState=active', 'ActiveState=failed')))(fixture_run(argv)))
    assert remote.plan(body)['plan_hash'] != before


@pytest.fixture
def executor(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, 'fcntl', SimpleNamespace(flock=MagicMock(), LOCK_EX=2, LOCK_NB=4))
    monkeypatch.setattr(remote.os, 'O_NOFOLLOW', 0, raising=False)
    monkeypatch.setattr(remote.os, 'open', MagicMock(return_value=99))
    monkeypatch.setattr(remote.os, 'close', MagicMock())
    monkeypatch.setattr(remote, 'journal', MagicMock())
    target = {'runtime': 'docker', 'id': 'a'*64, 'state': 'exited', 'revision': 'original'}
    inventory = {'hostname': 'test-vps', 'components': [{'key': 'bot', 'instances': [target]}]}
    monkeypatch.setattr(remote, 'discover', lambda: inventory)
    return inventory, target


def test_apply_targets_only_selected_container(monkeypatch, executor):
    inventory, selected = executor
    body = dict(component='bot', runtime='docker', instance=selected['id'], action='start')
    plan = remote.plan(body)
    commands = []
    def run(argv):
        commands.append(argv)
        selected['state'] = 'running'
        return 0, ''
    monkeypatch.setattr(remote, 'run', run)
    result = remote.execute(dict(body, operation='apply', plan_hash=plan['plan_hash'], confirmation='test-vps'))
    assert result['success']
    assert commands == [['docker', 'start', 'a'*64]]
    assert remote.journal.call_args.args[1] == 'complete'


def test_apply_rejects_changed_target(monkeypatch, executor):
    _, selected = executor
    body = dict(component='bot', runtime='docker', instance=selected['id'], action='start')
    plan = remote.plan(body)
    selected['revision'] = 'changed'
    command = MagicMock()
    monkeypatch.setattr(remote, 'run', command)
    with pytest.raises(ValueError, match='target_changed'):
        remote.execute(dict(body, operation='apply', plan_hash=plan['plan_hash'], confirmation='test-vps'))
    command.assert_not_called()


def test_successful_command_requires_state_verification(monkeypatch, executor):
    _, selected = executor
    body = dict(component='bot', runtime='docker', instance=selected['id'], action='start')
    plan = remote.plan(body)
    monkeypatch.setattr(remote, 'run', lambda argv: (0, ''))
    result = remote.execute(dict(body, operation='apply', plan_hash=plan['plan_hash'], confirmation='test-vps'))
    assert not result['success']
    assert remote.journal.call_args.args[1] == 'unconfirmed'


def test_shared_monitoring_catalog(monkeypatch):
    from app.services.ssh_service import SSHService
    service = SSHService()
    monkeypatch.setattr(service, 'get_connection_pooled', lambda *a: object())
    monkeypatch.setattr(service, '_probe_service', lambda client, descriptor: {'name': descriptor['name'], 'status': 'active'})
    data = service.get_services_stats('192.0.2.1', 'root', 'fixture')
    assert next(item for item in data if item['name'] == 'xray')['control_component'] == 'vless'
    assert next(item for item in data if item['name'] == 'ssh')['control_component'] is None
    for item in data:
        if item['control_component']:
            assert item['control_component'] in remote.CATALOG


def test_payload_is_standalone():
    from app.services.server_control_payload import SCRIPT_SOURCE
    scope = {'__name__': 'test_payload'}
    exec(compile(SCRIPT_SOURCE, '<payload>', 'exec'), scope)
    assert scope['CATALOG'] == remote.CATALOG
