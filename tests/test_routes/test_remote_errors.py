"""Понятные причины сбоя проверок по SSH (Disk usage, архивы, сброс, управление службами)."""
import socket
from unittest.mock import MagicMock, Mock

import paramiko
import pytest

from app.routes import reset as routes
from app.routes import server_control as control_routes
from app.routes.reset import RemoteConnectError, RemoteOutputError, describe_failure
from .test_reset import reset_client  # noqa: F401  (фикстура)
from .test_server_control import control_client  # noqa: F401  (фикстура)

CREDS = {"ip": "192.0.2.1", "port": 22542, "user": "root", "password": "fixture-only"}


def ssh_client(monkeypatch, connect_error=None, stdout_data=b'{"results": []}', status=0, stderr_data=b""):
    client = MagicMock()
    if connect_error is not None:
        client.connect.side_effect = connect_error
    stdin, stdout, stderr = MagicMock(), MagicMock(), MagicMock()
    stdout.read.return_value = stdout_data
    stdout.channel.recv_exit_status.return_value = status
    stderr.read.return_value = stderr_data
    client.exec_command.return_value = stdin, stdout, stderr
    monkeypatch.setattr(routes.paramiko, "SSHClient", lambda: client)
    return client


def test_unknown_host_policy_still_rejects():
    policy = routes.RejectUnknownHost()
    assert isinstance(policy, paramiko.RejectPolicy)
    with pytest.raises(routes.UnknownHostKeyError) as caught:
        policy.missing_host_key(Mock(), "[192.0.2.1]:22542", Mock())
    assert isinstance(caught.value, paramiko.SSHException)


@pytest.mark.parametrize("error,reason", [
    (routes.UnknownHostKeyError("not found in known_hosts"), "unknown_host"),
    (paramiko.BadHostKeyException("192.0.2.1", Mock(), Mock()), "changed_host"),
    (paramiko.AuthenticationException("denied"), "auth"),
    (socket.timeout("timed out"), "unreachable"),
    (ConnectionRefusedError(), "unreachable"),
    (paramiko.SSHException("Error reading SSH protocol banner"), "unreachable"),
])
def test_connect_failures_are_classified(monkeypatch, error, reason):
    client = ssh_client(monkeypatch, connect_error=error)
    with pytest.raises(RemoteConnectError) as caught:
        routes.remote(CREDS, [])
    assert caught.value.reason == reason
    client.exec_command.assert_not_called()
    client.close.assert_called_once()


@pytest.mark.parametrize("status,stderr_data,reason", [
    (127, b"bash: python3: command not found", "no_python"),
    (1, b"sudo: a password is required", "sudo_password"),
    (1, b"", "no_output"),
])
def test_empty_answer_is_classified_without_leaking_stderr(monkeypatch, status, stderr_data, reason):
    ssh_client(monkeypatch, stdout_data=b"", status=status, stderr_data=stderr_data)
    with pytest.raises(RemoteOutputError) as caught:
        routes.remote(dict(CREDS, user="admin"), [])
    assert caught.value.reason == reason
    assert str(caught.value) == reason  # только код причины, без stderr сервера


def test_card_credentials_do_not_spend_tries_on_local_keys(monkeypatch):
    client = ssh_client(monkeypatch)
    routes.remote(CREDS, [])
    kwargs = client.connect.call_args.kwargs
    assert kwargs["password"] == "fixture-only"
    assert kwargs["look_for_keys"] is False and kwargs["allow_agent"] is False
    # Без пароля и ключа в карточке — как раньше, ~/.ssh и ssh-agent.
    routes.remote(dict(CREDS, password=""), [])
    kwargs = client.connect.call_args.kwargs
    assert kwargs["look_for_keys"] is True and kwargs["allow_agent"] is True


def test_messages_name_the_cause_and_the_fix(app):
    with app.test_request_context("/"):
        assert "ssh -p 22542 root@192.0.2.1" in describe_failure(RemoteConnectError("unknown_host"), CREDS)
        assert "ssh-keygen -R '[192.0.2.1]:22542'" in describe_failure(RemoteConnectError("changed_host"), CREDS)
        assert "SSH" in describe_failure(RemoteConnectError("auth"), CREDS)
        assert "22542" in describe_failure(RemoteConnectError("unreachable"), CREDS)
        assert "python3" in describe_failure(RemoteOutputError("no_python"), CREDS)
        assert "sudo" in describe_failure(RemoteOutputError("sudo_password"), CREDS)
        # После запуска изменяющей команды точная причина неизвестна — только общий текст.
        assert describe_failure(RemoteOutputError("no_python"), CREDS, may_have_run=True) is None
        assert describe_failure(RemoteConnectError("auth"), CREDS, may_have_run=True)
        assert describe_failure(RuntimeError("private-detail"), CREDS) is None


def test_disk_usage_shows_known_hosts_hint(reset_client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(routes, "remote", Mock(side_effect=RemoteConnectError("unknown_host")))
    response = reset_client.post("/api/servers/one/disk-usage", json={}, headers={"X-CSRF-Token": "test-csrf"})
    assert response.status_code == 502
    error = response.get_json()["error"]
    assert "known_hosts" in error
    assert "ssh -p 22 root@192.0.2.1" in error


def test_control_discover_shows_auth_hint(control_client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(control_routes, "invoke", Mock(side_effect=RemoteConnectError("auth")))
    response = control_client.post("/api/servers/one/control/discover", json={}, headers={"X-CSRF-Token": "csrf"})
    assert response.status_code == 502
    assert "SSH" in response.get_json()["error"]
    assert "known_hosts and root/sudo -n" not in response.get_json()["error"]


def test_login_banner_before_the_marker_is_ignored(monkeypatch):
    banner = "Welcome to HIP-Hosting\n\xd0 not utf-8\n".encode("latin-1")
    client = ssh_client(monkeypatch, stdout_data=banner + routes.OUTPUT_MARKER.encode() + b'\n{"results": [1]}\n')
    assert routes.remote(CREDS, []) == {"results": [1]}
    command = client.exec_command.call_args.args[0]
    assert command.startswith("printf '%s\\n' " + routes.OUTPUT_MARKER + "; ")
    assert command.endswith("python3 -")


@pytest.mark.parametrize("stdout_data,status,stderr_data,reason", [
    (routes.OUTPUT_MARKER.encode() + b"\nnot json at all", 0, b"", "bad_output"),
    (routes.OUTPUT_MARKER.encode() + b"\n", 1, b"Traceback (most recent call last):", "python_error"),
])
def test_unparsable_answers_are_classified(monkeypatch, stdout_data, status, stderr_data, reason):
    ssh_client(monkeypatch, stdout_data=stdout_data, status=status, stderr_data=stderr_data)
    with pytest.raises(RemoteOutputError) as caught:
        routes.remote(CREDS, [])
    assert caught.value.reason == reason


def test_channel_failure_after_login_is_classified(monkeypatch):
    client = ssh_client(monkeypatch)
    client.exec_command.side_effect = paramiko.SSHException("channel closed")
    with pytest.raises(RemoteOutputError) as caught:
        routes.remote(CREDS, [])
    assert caught.value.reason == "exec_failed"


def test_new_messages(app):
    with app.test_request_context("/"):
        assert "ssh -p 22542 root@192.0.2.1 true" in describe_failure(RemoteOutputError("bad_output"), CREDS)
        assert "python3 --version" in describe_failure(RemoteOutputError("python_error"), CREDS)
        assert "python3 --version" in describe_failure(RemoteOutputError("no_output"), CREDS)
        assert describe_failure(RemoteOutputError("exec_failed"), CREDS)
        assert describe_failure(RemoteOutputError("bad_output"), CREDS, may_have_run=True) is None


def _ed25519_public_line():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
    return ed25519.Ed25519PrivateKey.generate().public_key().public_bytes(
        serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
    ).decode()


def test_unreadable_known_hosts_lines_do_not_hide_the_server_key(tmp_path, monkeypatch):
    public = _ed25519_public_line()
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".ssh" / "known_hosts").write_text(
        "@cert-authority *.example.com " + public + "\n"
        "broken.example.com ssh-ed25519 !!!not-base64!!!\n"
        "[192.0.2.1]:22542 " + public + "\n"
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    client = paramiko.SSHClient()
    routes._load_known_hosts(client)
    name = "[192.0.2.1]:22542"
    found = client._system_host_keys.lookup(name) or client.get_host_keys().lookup(name)
    assert found is not None and "ssh-ed25519" in found
    # Ключ другого сервера по-прежнему неизвестен — проверка остаётся строгой.
    assert not (client._system_host_keys.lookup("[192.0.2.9]:22") or client.get_host_keys().lookup("[192.0.2.9]:22"))


def test_unclassified_failure_names_only_the_exception_class(reset_client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(routes, "remote", Mock(side_effect=KeyError("secret-detail")))
    response = reset_client.post("/api/servers/one/disk-usage", json={}, headers={"X-CSRF-Token": "test-csrf"})
    assert response.status_code == 502
    error = response.get_json()["error"]
    assert error.endswith("(KeyError)")
    assert "secret-detail" not in error
