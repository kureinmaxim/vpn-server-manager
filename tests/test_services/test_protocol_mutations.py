import copy
import hashlib
import json
from pathlib import Path

import pytest
from app.services import protocol_mutations as edits


@pytest.fixture
def configs():
    manager = {'port': 443, 'server': 'example.com', 'private_extra': 'keep',
               'clients': [{'name': 'alice', 'password': 'fixture-one'}, {'name': 'bob', 'password': 'fixture-two'}]}
    runtime = {'log': {'level': 'warn'}, 'inbounds': [{'type': 'anytls', 'listen_port': 443,
        'users': copy.deepcopy(manager['clients']), 'tls': {'enabled': True,
            'certificate_path': '/etc/anytls/server.crt', 'key_path': '/etc/anytls/server.key'}}],
        'outbounds': [{'type': 'direct'}]}
    return manager, runtime


def test_pure_add_preserves_unknown_settings(configs):
    manager, runtime = configs
    updated, live = edits.changed_anytls(manager, runtime, {'kind': 'add_client', 'name': 'carol'}, password='generated')
    assert len(manager['clients']) == 2
    assert updated['private_extra'] == 'keep'
    assert live['log'] == runtime['log'] and live['outbounds'] == runtime['outbounds']
    assert live['inbounds'][0]['users'][-1] == {'name': 'carol', 'password': 'generated'}


def test_revoke_removes_live_credentials(configs):
    manager, runtime = edits.changed_anytls(*configs, {'kind': 'remove_client', 'name': 'alice'})
    assert manager['clients'] == runtime['inbounds'][0]['users'] == [{'name': 'bob', 'password': 'fixture-two'}]
    with pytest.raises(ValueError, match='last_client'):
        edits.changed_anytls(manager, runtime, {'kind': 'remove_client', 'name': 'bob'})


@pytest.mark.parametrize('change', [None, {'kind': 'port', 'port': True}, {'kind': 'port', 'port': 65536},
    {'kind': 'add_client', 'name': 'x;whoami'}, {'kind': 'add_client', 'name': 'alice', 'password': 'injection'},
    {'kind': 'remove_client', 'name': '../x'}])
def test_invalid_changes(change):
    with pytest.raises(ValueError): edits.validate_change(change)


def test_refuses_mismatched_live_config(configs):
    manager, runtime = configs
    runtime['inbounds'][0]['users'][0]['password'] = 'different'
    with pytest.raises(ValueError, match='config_mismatch'):
        edits.changed_anytls(manager, runtime, {'kind': 'port', 'port': 8443})


@pytest.fixture
def host(tmp_path, monkeypatch, configs):
    source, live = tmp_path / 'anytls_config.json', tmp_path / 'live.json'
    source.write_text(json.dumps(configs[0]))
    live.write_text(json.dumps(configs[1]))
    monkeypatch.setattr(edits, 'ANYTLS_CONFIG', live.as_posix())
    monkeypatch.setattr(edits, 'MUTATION_BACKUPS', str(tmp_path / 'backups'))
    monkeypatch.setattr(edits, 'sources', lambda *a: {'anytls': [(str(source), 'candidate')]})
    # Exercise transaction failure paths portably; Linux ownership/rename
    # primitives are separate from this in-memory service simulator.
    monkeypatch.setattr(edits, 'snapshot', lambda p: (Path(p).read_bytes(), Path(p).stat()))
    monkeypatch.setattr(edits, 'durable_replace', lambda p, raw, info: Path(p).write_bytes(raw))
    monkeypatch.setattr(edits, 'sync_directory', lambda p: None)
    monkeypatch.setattr(edits.time, 'sleep', lambda delay: None)
    def directory(path):
        path = Path(path); path.mkdir(parents=True, exist_ok=True); return path
    monkeypatch.setattr(edits, 'private_directory', directory)
    inventory = {'hostname': 'fixture-vps', 'components': [
        {'key': 'anytls', 'instances': [{'id': 'anytls.service', 'runtime': 'systemd', 'state': 'active'}]},
        {'key': 'bot', 'instances': []}]}
    commands = []
    outcomes = {'restart': [0], 'check': 0}
    def run(argv):
        commands.append(argv)
        if argv[:2] == ['systemctl', 'show']:
            return 0, '{ path=/usr/bin/sing-box ; argv[]=/usr/bin/sing-box run -c ' + live.as_posix() + ' ; ignore_errors=no ; }'
        if 'check' in argv: return outcomes['check'], ''
        if argv[:2] == ['systemctl', 'restart']:
            return outcomes['restart'].pop(0) if outcomes['restart'] else 0, ''
        if argv[:2] == ['systemctl', 'is-active']: return 0, 'active'
        raise AssertionError(argv)
    body = {'component': 'anytls', 'action': 'configure', 'source_id': hashlib.sha256(str(source).encode()).hexdigest(),
            'revision': hashlib.sha256(source.read_bytes()).hexdigest(), 'change': {'kind': 'add_client', 'name': 'carol'}}
    return source, live, inventory, run, body, outcomes


def execute(host):
    source, live, inventory, run, body, outcomes = host
    plan = edits.prepare_mutation(body, inventory, run)[0]
    assert 'fixture-one' not in json.dumps(plan) and 'fixture-two' not in json.dumps(plan)
    return edits.apply_mutation(dict(body, plan_hash=plan['plan_hash'], confirmation=plan['hostname']), inventory, run, lambda: inventory)


def test_apply_generates_secret_only_on_host_and_backups(host):
    source, live, *_ = host
    originals = (source.read_bytes(), live.read_bytes())
    result = execute(host)
    assert result['success']
    manager, runtime = json.loads(source.read_bytes()), json.loads(live.read_bytes())
    secret = manager['clients'][-1]['password']
    assert len(secret) >= 32 and secret not in json.dumps(result)
    assert runtime['inbounds'][0]['users'][-1]['password'] == secret
    assert (Path(result['backup']) / '0.json').read_bytes() == originals[0]
    assert (Path(result['backup']) / '1.json').read_bytes() == originals[1]


def test_restart_failure_restores_both_files(host):
    source, live, _, _, _, outcomes = host
    originals = (source.read_bytes(), live.read_bytes())
    outcomes['restart'] = [1, 0]
    result = execute(host)
    assert result['error'] == 'rolled_back'
    assert (source.read_bytes(), live.read_bytes()) == originals


def test_failed_recovery_blocks_next_plan(host):
    source, live, inventory, run, body, outcomes = host
    outcomes['restart'] = [1, 1]
    assert execute(host)['error'] == 'recovery_required'
    with pytest.raises(ValueError, match='recovery_required'):
        edits.prepare_mutation(body, inventory, run)


def test_validation_failure_never_changes_live_files(host):
    source, live, _, _, _, outcomes = host
    original = (source.read_bytes(), live.read_bytes())
    outcomes['check'] = 1
    assert execute(host)['error'] == 'validation_failed'
    assert original == (source.read_bytes(), live.read_bytes())


def test_running_bot_and_multiple_instances_block_edits(host):
    _, _, inventory, run, body, _ = host
    inventory['components'][1]['instances'] = [{'state': 'running'}]
    with pytest.raises(ValueError, match='bot_running'): edits.prepare_mutation(body, inventory, run)
    inventory['components'][1]['instances'] = []
    inventory['components'][0]['instances'] *= 2
    with pytest.raises(ValueError, match='unsupported_runtime'): edits.prepare_mutation(body, inventory, run)


def test_changed_revision_rejected_before_apply(host):
    source, live, inventory, run, body, _ = host
    plan = edits.prepare_mutation(body, inventory, run)[0]
    source.write_text('{}')
    before = live.read_bytes()
    with pytest.raises(ValueError, match='target_changed'):
        edits.apply_mutation(dict(body, plan_hash=plan['plan_hash'], confirmation=plan['hostname']), inventory, run, lambda: inventory)
    assert live.read_bytes() == before


def test_second_write_failure_rolls_back_first(host, monkeypatch):
    source, live, *_ = host
    originals = (source.read_bytes(), live.read_bytes())
    failed = False
    def replace(path, raw, info):
        nonlocal failed
        if Path(path) == live and not failed:
            failed = True
            raise OSError('simulated write failure')
        Path(path).write_bytes(raw)
    monkeypatch.setattr(edits, 'durable_replace', replace)
    result = execute(host)
    assert result['error'] == 'rolled_back'
    assert originals == (source.read_bytes(), live.read_bytes())


def test_external_edit_during_restart_is_not_overwritten(host):
    source, live, inventory, run, body, outcomes = host
    external = b'{"external":true}'
    def changed_run(argv):
        if argv[:2] == ['systemctl', 'restart']: source.write_bytes(external)
        return run(argv)
    result = execute((source, live, inventory, changed_run, body, outcomes))
    assert result['error'] == 'recovery_required'
    assert source.read_bytes() == external


def test_late_service_failure_triggers_rollback(host):
    source, live, inventory, run, body, outcomes = host
    checks = 0
    def unstable(argv):
        nonlocal checks
        if argv[:2] == ['systemctl', 'is-active']:
            checks += 1
            if checks == 2: return 3, 'failed'
        return run(argv)
    result = execute((source, live, inventory, unstable, body, outcomes))
    assert result['error'] == 'rolled_back'
