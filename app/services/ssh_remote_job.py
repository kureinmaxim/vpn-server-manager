"""Bounded, credential-free execution of a command over an already trusted SSH client."""
from dataclasses import dataclass
import time

import paramiko


class RemoteJobError(RuntimeError):
    """Sanitized remote execution failure; never contains server output."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class RemoteJobResult:
    stdout: bytes
    stderr: bytes
    exit_status: int


def run_remote_job(client, command, *, timeout, input_data=None, max_output_bytes=2 * 1024 * 1024):
    """Run one command with bounded output and a deadline for the whole job.

    The caller must provide a trusted/authenticated client and own its lifecycle.
    stdout is capped at ``max_output_bytes``. stderr is drained to avoid blocking
    the remote process, but only its first 16 KiB are retained for internal
    classification and must never be exposed to the user or written to logs.
    """
    channel = None
    try:
        stdin, stdout, _stderr = client.exec_command(command, timeout=timeout)
        channel = stdout.channel
        if input_data is not None:
            stdin.write(input_data)
            stdin.flush()
            stdin.channel.shutdown_write()
        output = bytearray()
        error_output = bytearray()
        deadline = time.monotonic() + timeout

        while True:
            received = False
            if channel.recv_ready():
                remaining = max_output_bytes - len(output)
                chunk = channel.recv(min(64 * 1024, remaining + 1))
                if chunk:
                    output.extend(chunk)
                    received = True
                if len(output) > max_output_bytes:
                    channel.close()
                    raise RemoteJobError('output_too_large')

            if channel.recv_stderr_ready():
                # Keep draining even after reaching the diagnostic cap so stderr
                # cannot fill the SSH channel window while stdout is being read.
                chunk = channel.recv_stderr(64 * 1024)
                if chunk:
                    if len(error_output) < 16 * 1024:
                        error_output.extend(chunk[:16 * 1024 - len(error_output)])
                    received = True

            if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
                return RemoteJobResult(bytes(output), bytes(error_output), channel.recv_exit_status())

            if not received:
                remaining_time = deadline - time.monotonic()
                if remaining_time <= 0:
                    channel.close()
                    raise RemoteJobError('timeout')
                time.sleep(min(0.01, remaining_time))
    except RemoteJobError:
        raise
    except (OSError, paramiko.SSHException) as exc:
        raise RemoteJobError('exec_failed') from exc
    except Exception as exc:
        raise RemoteJobError('exec_failed') from exc
