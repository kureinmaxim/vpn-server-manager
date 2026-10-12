from unittest.mock import Mock

from app.services.project_stats import COMMAND, PROJECTS, UNITS, parse_sample, summarize


def unit(name, cpu='2000000000', memory='104857600', pid='42', state='active', load='loaded'):
    return (f'Id={name}\nLoadState={load}\nActiveState={state}\nMainPID={pid}\n'
            f'ActiveEnterTimestampMonotonic=100\nCPUUsageNSec={cpu}\nMemoryCurrent={memory}\nTasksCurrent=4\n\n')


def sample(uptime, *units):
    return f'SAMPLE\nUP={uptime}\n' + ''.join(units)


def row(rows, name):
    return next(r for r in rows if r['name'] == name)


def test_interval_cpu_and_service_memory():
    rows = parse_sample(sample(100, unit('botcriptom.service'))
                        + sample(102, unit('botcriptom.service', cpu='5000000000')) + '\nDOCKER\nNO_DOCKER')
    bot = row(rows, 'botcriptom.service')
    assert bot['cpu_percent'] == 150  # CPU can span more than one core.
    assert bot['memory_bytes'] == 104857600 and bot['tasks'] == 4
    assert bot['project_name'] == 'BotCriptoM' and bot['group'] == 'project'


def test_unavailable_counters_and_failed_probe_are_not_zero():
    rows = parse_sample(sample(100, unit('botcriptom.service'))
                        + sample(101, unit('botcriptom.service', cpu='[not set]', memory='18446744073709551615')))
    assert row(rows, 'botcriptom.service')['cpu_percent'] is None
    assert row(rows, 'botcriptom.service')['memory_bytes'] is None
    assert all(r['status'] == 'unknown' for r in parse_sample(''))


def test_restarted_stopped_or_reset_service_has_no_misleading_cpu():
    first = sample(100, unit('rust-file-manager.service'))
    for second in (sample(101, unit('rust-file-manager.service', pid='99')),
                   sample(101, unit('rust-file-manager.service', state='inactive')),
                   sample(101, unit('rust-file-manager.service', cpu='0')),
                   sample(100, unit('rust-file-manager.service'))):
        assert row(parse_sample(first + second), 'rust-file-manager.service')['cpu_percent'] is None


def test_docker_states_distinguish_missing_docker_from_no_access():
    base = sample(100) + sample(101)
    running = parse_sample(base + '\nDOCKER\nbotcriptom|running\nbotcriptom-dash|exited\nother|running\nDOCKER_OK')
    assert row(running, 'botcriptom')['status'] == 'active'
    assert row(running, 'botcriptom-dash')['status'] == 'inactive'
    assert row(running, 'botcriptom-stop')['status'] == 'not_installed'
    assert all(r['name'] != 'other' for r in running)
    assert row(parse_sample(base + '\nDOCKER\nNO_DOCKER'), 'botcriptom')['status'] == 'not_installed'
    assert row(parse_sample(base + '\nDOCKER\n'), 'botcriptom')['status'] == 'unknown'


def test_summary_lists_only_found_projects_with_their_state():
    text = (sample(100, unit('botcriptom.service'), unit('botcriptom-dash.service', state='failed'),
                   unit('apix-server.service', load='not-found', state='inactive'))
            + sample(101, unit('botcriptom.service'), unit('botcriptom-dash.service', state='failed'),
                     unit('apix-server.service', load='not-found', state='inactive'),
                     unit('rust-file-manager.service'))
            + '\nDOCKER\nNO_DOCKER')
    projects = {p['key']: p for p in summarize(parse_sample(text))}
    assert projects['botcriptom']['state'] == 'partial'
    assert [c['name'] for c in projects['botcriptom']['components']] == ['botcriptom.service', 'botcriptom-dash.service']
    assert projects['rust_file_manager']['state'] == 'running'
    assert 'apix' not in projects
    assert all(p['state'] == 'unknown' for p in summarize(parse_sample('')))


def test_catalog_excludes_telegramonly_and_probe_is_read_only():
    assert 'telegramonly.service' not in UNITS
    assert not any(name.startswith(('ha-', 'shskm')) for name in UNITS)
    assert 'botcriptom.service' in COMMAND and 'docker ps' in COMMAND
    for forbidden in ('Environment', 'ExecStart', 'restart', 'docker inspect', 'docker logs'):
        assert forbidden not in COMMAND
    assert len({p['key'] for p in PROJECTS}) == len(PROJECTS)


def test_collector_failure_does_not_fail_server_snapshot():
    from app.services.ssh_service import SSHService
    service = SSHService()
    service._read_command_output = Mock(side_effect=TimeoutError)
    assert all(r['status'] == 'unknown' for r in service._collect_projects(Mock()))
