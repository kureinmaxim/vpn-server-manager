from concurrent.futures import ThreadPoolExecutor
import os
import shlex
import shutil
import subprocess
import threading
from unittest.mock import Mock

import pytest

from app.services.load_snapshot import SNAPSHOT_COMMAND, SNAPSHOT_SCRIPT, parse_snapshot
from app.services.ssh_service import SSHService

SAMPLE = """CPU1 100 10 30 500 50 5 5 0
TIME1 100.00
NET1 eth0 1000 2000
NET1 wg0 100 200
CPU2 130 10 40 540 60 5 15 0
TIME2 101.25
NET2 eth0 2250 4500
NET2 wg0 225 450
MEM MemTotal 8192
MEM MemFree 512
MEM Buffers 256
MEM Cached 1024
MEM MemAvailable 2048
LOAD 2.0 1.5 0.5
CORES 4
DISK 10000 6000 3500 64%
"""


def test_snapshot_uses_deltas_available_memory_and_real_elapsed_time():
    stats = parse_snapshot(SAMPLE)
    assert stats["cpu"]["used_pct"] == 50
    assert stats["memory"]["used_pct"] == 75
    assert stats["memory"]["available_bytes"] == 2048 * 1024
    assert stats["disk"]["available_bytes"] == 3500 * 1024
    assert stats["disk"]["used_pct"] == 64  # df accounts for reserved blocks.
    assert stats["load"] == {"averages": [2, 1.5, 0.5], "cores": 4, "per_core": 0.5}
    assert stats["network"]["rx_bytes_per_second"] == 1100
    assert stats["network"]["tx_bytes_per_second"] == 2200
    assert stats["network"]["interfaces"] == ["eth0", "wg0"]


def test_idle_is_valid_but_missing_metrics_are_not_zero():
    stats = parse_snapshot("CPU1 10 0 0 100 0 0 0 0\nCPU2 10 0 0 200 0 0 0 0")
    assert stats["cpu"]["used_pct"] == 0
    assert all(stats[key] is None for key in ("memory", "disk", "network", "load"))


def test_old_kernel_memory_fallback():
    stats = parse_snapshot(
        SAMPLE.replace("MEM MemAvailable 2048\n", "")
        + "MEM SReclaimable 128\nMEM Shmem 64\n"
    )
    assert stats["memory"]["available_bytes"] == (512 + 256 + 1024 + 128 - 64) * 1024


@pytest.mark.parametrize(
    "output", ["", "permission denied", "LOAD nan 0 0\nCORES 1", "DISK inf 1 1 2%"]
)
def test_unusable_output_is_an_error(output):
    with pytest.raises(ValueError):
        parse_snapshot(output)


def test_reset_and_missing_interfaces_do_not_produce_negative_or_spiking_rates():
    output = SAMPLE.replace("NET2 eth0 2250 4500", "NET2 eth0 2 4")
    stats = parse_snapshot(output + "NET2 tun0 9999999 9999999\n")
    assert stats["network"]["interfaces"] == ["wg0"]
    assert stats["network"]["rx_bytes_per_second"] == 100
    assert (
        parse_snapshot(output.replace("TIME2 101.25", "TIME2 100"))["network"] is None
    )


def test_single_bounded_command_reuses_pool_and_closes_channel(monkeypatch):
    service = SSHService()
    client, stdout = Mock(), Mock()
    stdout.read.return_value = SAMPLE.encode()
    client.exec_command.return_value = (Mock(), stdout, Mock())
    pooled = Mock(return_value=client)
    monkeypatch.setattr(service, "get_connection_pooled", pooled)
    assert service.get_load_snapshot("192.0.2.1", "admin", "secret", port=2222)["cpu"]
    pooled.assert_called_once_with(
        "192.0.2.1", 2222, "admin", "secret", connection_timeout=5
    )
    client.exec_command.assert_called_once_with(SNAPSHOT_COMMAND, timeout=8)
    stdout.channel.close.assert_called_once()
    stdout.read.side_effect = TimeoutError()
    with pytest.raises(TimeoutError):
        service.get_load_snapshot("192.0.2.1", "admin", "secret")
    assert stdout.channel.close.call_count == 2


def test_slow_connection_does_not_block_other_hosts(monkeypatch):
    monkeypatch.setattr(SSHService, "_connection_pool", {})
    monkeypatch.setattr(SSHService, "_connection_locks", {})
    started, release, fast_connected = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )

    def new_client():
        client = Mock()

        def connect(hostname, **kwargs):
            if hostname == "slow":
                started.set()
                assert release.wait(3)
            else:
                fast_connected.set()

        client.connect.side_effect = connect
        return client

    monkeypatch.setattr("app.services.ssh_service.paramiko.SSHClient", new_client)
    with ThreadPoolExecutor(max_workers=2) as executor:
        slow = executor.submit(
            SSHService.get_connection_pooled, "slow", 22, "root", "secret"
        )
        assert started.wait(1)
        fast = executor.submit(
            SSHService.get_connection_pooled, "fast", 22, "root", "secret"
        )
        try:
            assert fast_connected.wait(
                1
            ), "Other hosts must not wait for the slow SSH handshake"
        finally:
            release.set()
        assert slow.result() is not fast.result()


def test_failed_handshake_closes_client(monkeypatch):
    monkeypatch.setattr(SSHService, "_connection_pool", {})
    monkeypatch.setattr(SSHService, "_connection_locks", {})
    client = Mock()
    client.connect.side_effect = TimeoutError()
    monkeypatch.setattr(
        "app.services.ssh_service.paramiko.SSHClient", Mock(return_value=client)
    )
    with pytest.raises(TimeoutError):
        SSHService.get_connection_pooled("timeout", 22, "root", "secret")
    client.close.assert_called_once()
    assert not SSHService._connection_pool


@pytest.mark.skipif(
    not shutil.which("sh") or not shutil.which("awk"), reason="POSIX shell required"
)
def test_shell_collector_with_linux_proc_fixtures(tmp_path):
    """Exercise real sh/awk field extraction, not just a handwritten wire format."""
    proc = tmp_path / "proc"
    (proc / "net").mkdir(parents=True)
    (proc / "stat").write_text("cpu 100 10 30 500 50 5 5 0 0 0\n")
    (proc / "uptime").write_text("100.00 99.00\n")
    (proc / "meminfo").write_text("MemTotal: 8192 kB\nMemAvailable: 2048 kB\n")
    (proc / "loadavg").write_text("2.0 1.5 0.5 1/200 300\n")

    def net_line(name, rx, tx):
        return f" {name}: {rx} 0 0 0 0 0 0 0 {tx} 0 0 0 0 0 0 0\n"

    (proc / "net/dev").write_text(
        net_line("eth0", 1000, 2000)
        + net_line("lo", 99999, 99999)
        + net_line("veth123", 99999, 99999)
    )
    binaries = tmp_path / "bin"
    binaries.mkdir()
    scripts = {
        "sleep": (
            f"printf 'cpu 130 10 40 540 60 5 15 0 0 0\\n' > {shlex.quote(str(proc / 'stat'))}\n"
            f"printf '101.25 100.00\\n' > {shlex.quote(str(proc / 'uptime'))}\n"
            f"printf '%s' {shlex.quote(net_line('eth0', 2250, 4500))} > {shlex.quote(str(proc / 'net/dev'))}"
        ),
        "getconf": "printf '4\\n'",
        "df": "printf 'Filesystem 1024-blocks Used Available Capacity Mounted\\n/dev/vda 10000 6000 3500 64%% /\\n'",
    }
    for name, script in scripts.items():
        executable = binaries / name
        executable.write_text("#!/bin/sh\n" + script + "\n")
        executable.chmod(0o755)
    # Only substitute fixture paths; run the actual production shell pipeline.
    command = SNAPSHOT_SCRIPT.replace("/proc/", str(proc) + "/")
    completed = subprocess.run(
        ["sh", "-c", command],
        env={**os.environ, "PATH": str(binaries) + os.pathsep + os.environ["PATH"]},
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    assert completed.stderr == ""
    stats = parse_snapshot(completed.stdout)
    assert stats["cpu"]["used_pct"] == 50
    assert stats["network"]["interfaces"] == ["eth0"]
    assert stats["network"]["rx_bytes_per_second"] == 1000
    assert stats["network"]["tx_bytes_per_second"] == 2000
    assert stats["disk"]["available_bytes"] == 3500 * 1024
    assert stats["memory"]["used_pct"] == 75
    assert stats["load"]["cores"] == 4
