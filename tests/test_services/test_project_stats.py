import json
import os
from unittest.mock import Mock

import pytest

from app.services.dns_mail_probe import ROLE_NAMES
from app.services.project_stats import (ADGUARD, CHATMAIL, DEFAULT_PROJECTS, EXAMPLE_PROJECTS, FILE_MANAGER,
                                        ProjectError, build_command,
                                        clean_projects, load_projects, parse_sample, save_projects, summarize)

PROJECTS = clean_projects([
    {'name': 'Web application', 'units': ['web-app', 'web-app-api', 'web-app-worker'],
     'containers': ['web-app', 'web-db']},
    {'name': 'File service', 'units': ['file-service', 'file-bridge']},
    {'name': 'Mesh service', 'units': ['mesh-bridge', 'mesh-daemon', 'relay', 'mesh-watchdog.timer'],
     'containers': ['mesh-bridge', 'mesh-node'], 'processes': ['relay', 'mesh-agent']},
    {'name': 'Dashboard', 'containers': ['dashboard']},
    {'name': 'Control plane', 'units': ['control-plane', 'control-ui'],
     'containers': ['control-plane', 'control-ui']},
    {'name': ADGUARD['name'], 'units': ADGUARD['units'], 'containers': ['adguardhome']},
    {'name': CHATMAIL['name'], 'units': CHATMAIL['units']},
])


def unit(name, cpu='2000000000', memory='104857600', pid='42', state='active', load='loaded'):
    return (f'Id={name}\nLoadState={load}\nActiveState={state}\nMainPID={pid}\n'
            f'ActiveEnterTimestampMonotonic=100\nCPUUsageNSec={cpu}\nMemoryCurrent={memory}\nTasksCurrent=4\n\n')


def sample(uptime, *units):
    return f'SAMPLE\nUP={uptime}\n' + ''.join(units)


def row(rows, name):
    return next(r for r in rows if r['name'] == name)


def test_interval_cpu_and_service_memory():
    rows = parse_sample(sample(100, unit('web-app.service'))
                        + sample(102, unit('web-app.service', cpu='5000000000')) + '\nDOCKER\nNO_DOCKER', PROJECTS)
    bot = row(rows, 'web-app.service')
    assert bot['cpu_percent'] == 150  # CPU can span more than one core.
    assert bot['memory_bytes'] == 104857600 and bot['tasks'] == 4
    assert bot['project_name'] == 'Web application' and bot['group'] == 'project'


def test_unavailable_counters_and_failed_probe_are_not_zero():
    rows = parse_sample(sample(100, unit('web-app.service'))
                        + sample(101, unit('web-app.service', cpu='[not set]', memory='18446744073709551615')), PROJECTS)
    assert row(rows, 'web-app.service')['cpu_percent'] is None
    assert row(rows, 'web-app.service')['memory_bytes'] is None
    assert all(r['status'] == 'unknown' for r in parse_sample('', PROJECTS))


def test_restarted_stopped_or_reset_service_has_no_misleading_cpu():
    first = sample(100, unit('file-service.service'))
    for second in (sample(101, unit('file-service.service', pid='99')),
                   sample(101, unit('file-service.service', state='inactive')),
                   sample(101, unit('file-service.service', cpu='0')),
                   sample(100, unit('file-service.service'))):
        assert row(parse_sample(first + second, PROJECTS), 'file-service.service')['cpu_percent'] is None


def test_docker_states_distinguish_missing_docker_from_no_access():
    base = sample(100) + sample(101)
    running = parse_sample(base + '\nDOCKER\nweb-app|running\ndashboard|exited\nother|running\nDOCKER_OK', PROJECTS)
    assert row(running, 'web-app')['status'] == 'active'
    assert row(running, 'dashboard')['status'] == 'inactive'
    assert row(running, 'web-db')['status'] == 'not_installed'
    assert all(r['name'] != 'other' for r in running)
    assert row(parse_sample(base + '\nDOCKER\nNO_DOCKER', PROJECTS), 'web-app')['status'] == 'unknown'
    assert row(parse_sample(base + '\nDOCKER\n', PROJECTS), 'web-app')['status'] == 'unknown'


def test_container_only_project_stays_visible_when_docker_is_unavailable():
    projects = clean_projects([{'name': 'Container app', 'containers': ['container-app']}])
    rows = parse_sample(sample(100) + sample(101) + '\nDOCKER\nNO_DOCKER', projects)
    [project] = summarize(rows, projects)
    assert project['state'] == 'unknown'
    assert project['components'][0]['kind'] == 'container'
    assert project['components'][0]['status'] == 'unknown'


def test_summary_lists_only_found_projects_with_their_state():
    text = (sample(100, unit('web-app.service'), unit('web-app-api.service', state='failed'),
                   unit('web-app-worker.service', load='not-found', state='inactive'),
                   unit('control-plane.service', load='not-found', state='inactive'),
                   unit('control-ui.service', load='not-found', state='inactive'),
                   unit('mesh-bridge.service', load='not-found', state='inactive'),
                   unit('mesh-daemon.service', load='not-found', state='inactive'),
                   unit('mesh-watchdog.timer', load='not-found', state='inactive'))
            + sample(101, unit('web-app.service'), unit('web-app-api.service', state='failed'),
                     unit('web-app-worker.service', load='not-found', state='inactive'),
                     unit('control-plane.service', load='not-found', state='inactive'),
                     unit('control-ui.service', load='not-found', state='inactive'),
                     unit('mesh-bridge.service', load='not-found', state='inactive'),
                     unit('mesh-daemon.service', load='not-found', state='inactive'),
                     unit('mesh-watchdog.timer', load='not-found', state='inactive'),
                     unit('relay.service'))
            + '\nPROC\nP=relay=0\nP=mesh-agent=0\nPROC_OK\nDOCKER\nDOCKER_OK')
    projects = {p['name']: p for p in summarize(parse_sample(text, PROJECTS), PROJECTS)}
    assert projects['Web application']['state'] == 'partial'
    assert [c['name'] for c in projects['Web application']['components']] == [
        'web-app.service', 'web-app-api.service']
    assert projects['Mesh service']['state'] == 'running'
    assert 'Control plane' not in projects
    assert all(p['state'] == 'unknown' for p in summarize(parse_sample('', PROJECTS), PROJECTS))


def test_default_catalog_and_read_only_probe():
    names = [p['name'] for p in PROJECTS]
    assert DEFAULT_PROJECTS == []
    assert load_projects() == []
    assert {'Web application example', 'Background worker example'} == {
        p['name'] for p in clean_projects(EXAMPLE_PROJECTS)}
    assert FILE_MANAGER['name'] == 'Rust File Manager' and 'rust-file-manager' in FILE_MANAGER['units']
    assert CHATMAIL['name'] == ROLE_NAMES['chatmail'] and 'doveauth' in CHATMAIL['units']
    assert ADGUARD['name'] == ROLE_NAMES['adguard']
    assert not any('example' in p['name'].lower() for p in load_projects())
    units = [u for p in PROJECTS for u in p['units']]
    assert 'web-app.service' not in build_command([])
    command = build_command(PROJECTS)
    assert 'web-app.service' in command and 'docker ps' in command
    for forbidden in ('Environment', 'ExecStart', 'restart', 'docker inspect', 'docker logs'):
        assert forbidden not in command


def test_reticulum_found_via_ha_bridge_and_watchdog_timer():
    states = (unit('mesh-bridge.service'), unit('mesh-watchdog.timer', pid='0'),
              unit('relay.service', load='not-found', state='inactive'),
              unit('mesh-daemon.service', load='not-found', state='inactive'))
    text = (sample(100, *states) + sample(101, *states)
            + '\nPROC\nP=relay=0\nP=mesh-agent=0\nPROC_OK\nDOCKER\nDOCKER_OK')
    assert 'mesh-watchdog.timer ' in build_command(PROJECTS) + ' '
    assert 'mesh-watchdog.timer.service' not in build_command(PROJECTS)
    project = next(p for p in summarize(parse_sample(text, PROJECTS), PROJECTS) if p['name'] == 'Mesh service')
    assert project['state'] == 'running'
    assert [c['name'] for c in project['components']] == ['mesh-bridge.service', 'mesh-watchdog.timer']
    missing = (unit('mesh-bridge.service', load='not-found', state='inactive'),
               unit('mesh-daemon.service', load='not-found', state='inactive'),
               unit('relay.service', load='not-found', state='inactive'),
               unit('mesh-watchdog.timer', load='not-found', state='inactive'))
    docker = parse_sample(sample(100, *missing) + sample(101, *missing)
                          + '\nPROC\nP=relay=0\nP=mesh-agent=0\nPROC_OK'
                          + '\nDOCKER\nmesh-bridge|running\nDOCKER_OK', PROJECTS)
    project = next(p for p in summarize(docker, PROJECTS) if p['name'] == 'Mesh service')
    assert project['state'] == 'running' and project['components'][0]['name'] == 'mesh-bridge'


def test_manually_started_processes_are_counted_by_name_only():
    command = build_command(PROJECTS)
    assert "for p in relay mesh-agent;" in command and 'pgrep -x -- "$p"' in command
    assert 'pgrep -f' not in command and '/proc/' + '*/cmdline' not in command
    absent_units = (unit('mesh-bridge.service', load='not-found', state='inactive'),
                    unit('mesh-daemon.service', load='not-found', state='inactive'),
                    unit('relay.service', load='not-found', state='inactive'),
                    unit('mesh-watchdog.timer', load='not-found', state='inactive'))
    base = sample(100, *absent_units) + sample(101, *absent_units)
    rows = parse_sample(base + '\nPROC\nP=relay=2\nP=mesh-agent=0\nPROC_OK\nDOCKER\nDOCKER_OK', PROJECTS)
    assert row(rows, 'relay')['status'] == 'active' and row(rows, 'relay')['count'] == 2
    assert row(rows, 'mesh-agent')['status'] == 'not_installed'
    project = next(p for p in summarize(rows, PROJECTS) if p['name'] == 'Mesh service')
    assert project['state'] == 'running' and [c['kind'] for c in project['components']] == ['process']
    rows = parse_sample(sample(100, *absent_units, unit('relay.service'))
                        + sample(101, *absent_units, unit('relay.service'))
                        + '\nPROC\nP=relay=1\nP=mesh-agent=0\nPROC_OK\nDOCKER\nDOCKER_OK', PROJECTS)
    project = next(p for p in summarize(rows, PROJECTS) if p['name'] == 'Mesh service')
    assert [(c['kind'], c['name']) for c in project['components']] == [('unit', 'relay.service')]
    for missing in ('\nPROC\nNO_PGREP\nDOCKER\nNO_DOCKER', '\nPROC\nP=relay=1\n', ''):
        assert row(parse_sample(base + missing, PROJECTS), 'relay')['status'] == 'unknown'


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


def test_role_discovery_is_not_listed_twice():
    text = (sample(100, unit('AdGuardHome.service'))
            + sample(101, unit('AdGuardHome.service')) + '\nDOCKER\nNO_DOCKER')
    rows = parse_sample(text, PROJECTS)
    rows.append({'name': ROLE_NAMES['adguard'], 'display_name': ROLE_NAMES['adguard'],
                 'kind': 'role', 'group': 'project', 'project': 'adguard',
                 'project_name': ROLE_NAMES['adguard'], 'status': 'unknown',
                 'control_component': None,
                 'role_summary': {'key': 'adguard', 'name': ROLE_NAMES['adguard'],
                                  'discovery': 'detected', 'state': 'running',
                                  'components': [{'name': 'adguard', 'status': 'active'}]}})
    found = [p['name'] for p in summarize(rows, PROJECTS)]
    assert found.count(ROLE_NAMES['adguard']) == 1
    assert next(p for p in summarize(rows, PROJECTS) if p['name'] == ROLE_NAMES['adguard'])['discovery'] == 'detected'


def test_unconfigured_and_invalid_catalogs_stay_empty(app):
    assert load_projects(app) == []
    path = os.path.join(app.config['APP_DATA_DIR'], 'config.json')
    json.dump({'tracked_projects': [{'name': 'bad', 'units': ['$(id)']}]}, open(path, 'w'))
    assert load_projects(app) == []


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
    assert load_projects(app) == []
    json.dump({'tracked_projects': [{'name': 'bad', 'units': ['$(id)']}]}, open(path, 'w'))
    assert load_projects(app) == []


def test_collector_failure_does_not_fail_server_snapshot():
    from app.services.ssh_service import SSHService
    service = SSHService()
    service._read_command_output = Mock(side_effect=TimeoutError)
    assert all(r['status'] == 'unknown' for r in service._collect_projects(Mock(), PROJECTS))
