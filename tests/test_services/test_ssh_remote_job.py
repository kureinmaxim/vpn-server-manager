"""Bounded remote job I/O with no raw stderr or exception text in errors."""
from collections import deque
from unittest.mock import Mock

import paramiko
import pytest

from app.services.ssh_remote_job import RemoteJobError, run_remote_job


class FakeChannel:
    def __init__(self, stdout=(), stderr=(), exit_status=0):
        self.stdout = deque(stdout)
        self.stderr = deque(stderr)
        self.exit_status = exit_status
        self.closed = False

    @staticmethod
    def _take(chunks, size):
        chunk = chunks.popleft()
        if len(chunk) > size:
            chunks.appendleft(chunk[size:])
            return chunk[:size]
        return chunk

    def recv_ready(self):
        return bool(self.stdout)

    def recv_stderr_ready(self):
        return bool(self.stderr)

    def recv(self, size):
        return self._take(self.stdout, size)

    def recv_stderr(self, size):
        return self._take(self.stderr, size)

    def exit_status_ready(self):
        return not self.stdout and not self.stderr

    def recv_exit_status(self):
        return self.exit_status

    def close(self):
        self.closed = True


def test_run_remote_job_sends_stdin_and_returns_bounded_stdout_and_exit_status():
    client = Mock()
    channel = FakeChannel([b'job output'], [b'remote detail'], exit_status=3)
    stdin, stdout, stderr = Mock(), Mock(), Mock()
    stdout.channel = channel
    client.exec_command.return_value = stdin, stdout, stderr
    stdin.channel = Mock()

    result = run_remote_job(client, 'python3 -', timeout=12, input_data='script', max_output_bytes=64)

    assert result.stdout == b'job output'
    assert result.stderr == b'remote detail'
    assert result.exit_status == 3
    client.exec_command.assert_called_once_with('python3 -', timeout=12)
    stdin.write.assert_called_once_with('script')
    stdin.flush.assert_called_once_with()
    stdin.channel.shutdown_write.assert_called_once_with()


def test_run_remote_job_rejects_output_over_limit():
    client = Mock()
    channel = FakeChannel([b'four'])
    stdout = Mock(channel=channel)
    client.exec_command.return_value = Mock(), stdout, Mock()

    with pytest.raises(RemoteJobError) as caught:
        run_remote_job(client, 'cat', timeout=1, max_output_bytes=3)

    assert caught.value.reason == 'output_too_large'
    assert str(caught.value) == 'output_too_large'
    assert channel.closed


def test_run_remote_job_drains_stderr_beyond_diagnostic_limit():
    client = Mock()
    stderr_data = b'x' * (64 * 1024 + 123)
    channel = FakeChannel([b'ok'], [stderr_data])
    stdout = Mock(channel=channel)
    client.exec_command.return_value = Mock(), stdout, Mock()

    result = run_remote_job(client, 'noisy-command', timeout=1)

    assert result.stdout == b'ok'
    assert result.stderr == b'x' * (16 * 1024)
    assert not channel.stderr


def test_run_remote_job_hides_remote_exception_text():
    client = Mock()
    client.exec_command.side_effect = paramiko.SSHException('private remote detail')

    with pytest.raises(RemoteJobError) as caught:
        run_remote_job(client, 'true', timeout=1)

    assert caught.value.reason == 'exec_failed'
    assert 'private remote detail' not in str(caught.value)
