from app.services.file_manager_stats import COMMAND, parse_sample


def sample(uptime, cpu='2000000000', memory='104857600', pid='42', state='active', load='loaded'):
    return (f'SAMPLE\nUP={uptime}\nId=rust-file-manager.service\nLoadState={load}\n'
            f'ActiveState={state}\nMainPID={pid}\nActiveEnterTimestampMonotonic=100\n'
            f'CPUUsageNSec={cpu}\nMemoryCurrent={memory}\nTasksCurrent=4\n\n'
            'Id=rfm-internal-bridge.service\nLoadState=not-found\nActiveState=inactive\n\n')


def test_interval_cpu_and_service_memory():
    rows = parse_sample(sample(100) + sample(102, cpu='5000000000'))
    assert rows[0]['cpu_percent'] == 150  # CPU can span more than one core.
    assert rows[0]['memory_bytes'] == 104857600
    assert rows[0]['tasks'] == 4
    assert rows[1]['status'] == 'not_installed'
    assert rows[1]['memory_bytes'] is None


def test_unavailable_counters_and_permission_failure_are_not_zero():
    row = parse_sample(sample(100) + sample(101, cpu='[not set]', memory='18446744073709551615'))[0]
    assert row['cpu_percent'] is None
    assert row['memory_bytes'] is None
    assert all(r['status'] == 'unknown' for r in parse_sample(''))


def test_restarted_stopped_or_reset_service_has_no_misleading_cpu():
    for second in (sample(101, pid='99'), sample(101, state='inactive'),
                   sample(101, cpu='0'), sample(100)):
        assert parse_sample(sample(100) + second)[0]['cpu_percent'] is None


def test_probe_only_reads_allowlisted_systemd_properties():
    assert 'Environment' not in COMMAND
    assert 'ExecStart' not in COMMAND
    assert 'restart' not in COMMAND
    assert 'rust-file-manager.service' in COMMAND


def test_collector_failure_does_not_fail_server_snapshot():
    from unittest.mock import Mock
    from app.services.ssh_service import SSHService
    service = SSHService()
    service._read_command_output = Mock(side_effect=TimeoutError)
    assert service._collect_file_manager(Mock())[0]['status'] == 'unknown'
