import json
import os
from unittest.mock import Mock

import pytest

from app.services.project_stats import (DEFAULT_PROJECTS, ProjectError, build_command, clean_projects,
                                        load_projects, parse_sample, save_projects, summarize)

PROJECTS = clean_projects(DEFAULT_PROJECTS)


def unit(name, cpu='2000000000', memory='104857600', pid='42', state='active', load='loaded'):
    return (f'Id={name}\nLoadState={load}\nActiveState={state}\nMainPID={pid}\n'
            f'ActiveEnterTimestampMonotonic=100\nCPUUsageNSec={cpu}\nMemoryCurrent={memory}\nTasksCurrent=4\n\n')


def sample(uptime, *units):
    return f'SAMPLE\nUP={uptime}\n' + ''.join(units)


def row(rows, name):
    return next(r for r in rows if r['name'] == name)


def test_interval_cpu_and_service_memory():
    rows = parse_sample(sample(100, unit('botcriptom.service'))
                        + sample(102, unit('botcriptom.service', cpu='5000000000')) + '\nDOCKER\nNO_DOCKER', PROJECTS)
    bot = row(rows, 'botcriptom.service')
    assert bot['cpu_percent'] == 150  # CPU can span more than one core.
    assert bot['memory_bytes'] == 104857600 and bot['tasks'] == 4
    assert bot['project_name'] == 'BotCriptoM' and bot['group'] == 'project'


def test_unavailable_counters_and_failed_probe_are_not_zero():
    rows = parse_sample(sample(100, unit('botcriptom.service'))
                        + sample(101, unit('botcriptom.service', cpu='[not set]', memory='18446744073709551615')), PROJECTS)
    assert row(rows, 'botcriptom.service')['cpu_percent'] is None
    assert row(rows, 'botcriptom.service')['memory_bytes'] is None
    assert all(r['status'] == 'unknown' for r in parse_sample('', PROJECTS))


def test_restarted_stopped_or_reset_service_has_no_misleading_cpu():
    first = sample(100, unit('rust-file-manager.service'))
    for second in (sample(101, unit('rust-file-manager.service', pid='99')),
                   sample(101, unit('rust-file-manager.service', state='inactive')),
                   sample(101, unit('rust-file-manager.service', cpu='0')),
                   sample(100, unit('rust-file-manager.service'))):
        assert row(parse_sample(first + second, PROJECTS), 'rust-file-manager.service')['cpu_percent'] is None


def test_docker_states_distinguish_missing_docker_from_no_access():
    base = sample(100) + sample(101)
    running = parse_sample(base + '\nDOCKER\nbotcriptom|running\ndockhand|exited\nother|running\nDOCKER_OK', PROJECTS)
    assert row(running, 'botcriptom')['status'] == 'active'
    assert row(running, 'dockhand')['status'] == 'inactive'
    assert row(running, 'botcriptom-stop')['status'] == 'not_installed'
    assert all(r['name'] != 'other' for r in running)
    assert row(parse_sample(base + '\nDOCKER\nNO_DOCKER', PROJECTS), 'botcriptom')['status'] == 'not_installed'
    assert row(parse_sample(base + '\nDOCKER\n', PROJECTS), 'botcriptom')['status'] == 'unknown'


def test_summary_lists_only_found_projects_with_their_state():
    text = (sample(100, unit('botcriptom.service'), unit('botcriptom-dash.service', state='failed'),
                   unit('headscale.service', load='not-found', state='inactive'))
            + sample(101, unit('botcriptom.service'), unit('botcriptom-dash.service', state='failed'),
                     unit('headscale.service', load='not-found', state='inactive'),
                     unit('rnsd.service'))
            + '\nDOCKER\nNO_DOCKER')
    projects = {p['name']: p for p in summarize(parse_sample(text, PROJECTS), PROJECTS)}
    assert projects['BotCriptoM']['state'] == 'partial'
    assert [c['name'] for c in projects['BotCriptoM']['components']] == ['botcriptom.service', 'botcriptom-dash.service']
    assert projects['Reticulum']['state'] == 'running'
    assert 'Headscale / Headplane' not in projects
    assert all(p['state'] == 'unknown' for p in summarize(parse_sample('', PROJECTS), PROJECTS))


def test_default_catalog_and_read_only_probe():
    names = [p['name'] for p in PROJECTS]
    assert names[:3] == ['BotCriptoM', 'Rust File Manager', 'UGCTL (UDP gRPC COM Lite)']
    assert {'Reticulum', 'Dockhand', 'Headscale / Headplane'} <= set(names)
    assert not any(n in names for n in ('ApiAigRPC', 'ApiNgRPC', 'ApiXgRPC', 'TelegramHelper', 'PDF3MD'))
    units = [u for p in PROJECTS for u in p['units']]
    assert 'telegramonly' not in units and not any(u.startswith(('ha-stub', 'ha-adapter', 'shskm')) for u in units)
    command = build_command(PROJECTS)
    assert 'botcriptom.service' in command and 'docker ps' in command
    for forbidden in ('Environment', 'ExecStart', 'restart', 'docker inspect', 'docker logs'):
        assert forbidden not in command


def test_reticulum_found_via_ha_bridge_and_watchdog_timer():
    states = (unit('ha-reticulum-bridge.service'), unit('ha-rns-watchdog.timer', pid='0'),
              unit('reticulum.service', load='not-found', state='inactive'))
    text = sample(100, *states) + sample(101, *states) + '\nDOCKER\nNO_DOCKER'
    assert 'ha-rns-watchdog.timer ' in build_command(PROJECTS) + ' '
    assert 'ha-rns-watchdog.timer.service' not in build_command(PROJECTS)
    reticulum = next(p for p in summarize(parse_sample(text, PROJECTS), PROJECTS) if p['name'] == 'Reticulum')
    assert reticulum['state'] == 'running'
    assert [c['name'] for c in reticulum['components']] == ['ha-reticulum-bridge.service', 'ha-rns-watchdog.timer']
    docker = parse_sample(sample(100) + sample(101) + '\nDOCKER\nha_rns_bridge|running\nDOCKER_OK', PROJECTS)
    reticulum = next(p for p in summarize(docker, PROJECTS) if p['name'] == 'Reticulum')
    assert reticulum['state'] == 'running' and reticulum['components'][0]['name'] == 'ha_rns_bridge'


def test_manually_started_processes_are_counted_by_name_only():
    command = build_command(PROJECTS)
    assert "for p in rnsd lxmd;" in command and 'pgrep -x -- "$p"' in command
    assert 'pgrep -f' not in command and '/proc/' + '*/cmdline' not in command
    base = sample(100) + sample(101)
    rows = parse_sample(base + '\nPROC\nP=rnsd=2\nP=lxmd=0\nPROC_OK\nDOCKER\nNO_DOCKER', PROJECTS)
    assert row(rows, 'rnsd')['status'] == 'active' and row(rows, 'rnsd')['count'] == 2
    assert row(rows, 'lxmd')['status'] == 'not_installed'
    reticulum = next(p for p in summarize(rows, PROJECTS) if p['name'] == 'Reticulum')
    assert reticulum['state'] == 'running' and [c['kind'] for c in reticulum['components']] == ['process']
    rows = parse_sample(sample(100, unit('rnsd.service')) + sample(101, unit('rnsd.service')) + '\nPROC\nP=rnsd=1\nP=lxmd=0\nPROC_OK', PROJECTS)
    reticulum = next(p for p in summarize(rows, PROJECTS) if p['name'] == 'Reticulum')
    assert [(c['kind'], c['name']) for c in reticulum['components']] == [('unit', 'rnsd.service')]
    for missing in ('\nPROC\nNO_PGREP\nDOCKER\nNO_DOCKER', '\nPROC\nP=rnsd=1\n', ''):
        assert row(parse_sample(base + missing, PROJECTS), 'rnsd')['status'] == 'unknown'


def test_custom_projects_are_validated_before_reaching_the_shell():
    projects = clean_projects([{'name': '  My   app ', 'units': 'myapp.service, myapp-worker myapp', 'containers': ''},
                               {'name': '', 'units': '', 'containers': ''},
                               {'name': 'My app', 'units': [], 'containers': ['web']}])
    assert projects == [{'key': 'my_app', 'name': 'My app', 'units': ['myapp', 'myapp-worker'], 'containers': [], 'processes': []},
                        {'key': 'my_app_', 'name': 'My app', 'units': [], 'containers': ['web'], 'processes': []}]
    assert clean_projects([{'name': 'Manual', 'processes': 'rnsd lxmd'}])[0]['processes'] == ['rnsd', 'lxmd']
    for bad in ('a' * 16, 'x@y', '$(id)'):
        with pytest.raises(ProjectError):
            clean_projects([{'name': 'evil', 'processes': [bad]}])
    assert 'docker' not in build_command(projects[:1]) and 'myapp-worker.service' in build_command(projects)
    for bad in ('x; rm -rf /', '$(id)', 'a`b`', '-flag', 'a' * 65):
        with pytest.raises(ProjectError):
            clean_projects([{'name': 'evil', 'units': [bad]}])
    with pytest.raises(ProjectError):
        clean_projects([{'name': 'no components', 'units': ''}])
    assert build_command([]).count('systemctl') == 0


def test_saved_list_persists_next_to_ui_preferences_and_resets(app):
    path = os.path.join(app.config['APP_DATA_DIR'], 'config.json')
    with open(path, 'w') as handle:
        json.dump({'ui': {'language': 'en', 'zoom': '80'}}, handle)
    assert save_projects(app, [{'name': 'Blog', 'units': 'ghost', 'containers': ''}])
    stored = json.load(open(path))
    assert stored['ui'] == {'language': 'en', 'zoom': '80'}
    assert [p['name'] for p in load_projects(app)] == ['Blog']
    assert save_projects(app, [])
    assert load_projects(app) == []
    assert save_projects(app, None)
    assert [p['name'] for p in load_projects(app)] == [p['name'] for p in PROJECTS]
    json.dump({'tracked_projects': [{'name': 'bad', 'units': ['$(id)']}]}, open(path, 'w'))
    assert [p['name'] for p in load_projects(app)] == [p['name'] for p in PROJECTS]


def test_collector_failure_does_not_fail_server_snapshot():
    from app.services.ssh_service import SSHService
    service = SSHService()
    service._read_command_output = Mock(side_effect=TimeoutError)
    assert all(r['status'] == 'unknown' for r in service._collect_projects(Mock(), PROJECTS))
