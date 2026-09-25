import time
from unittest.mock import MagicMock

import paramiko
import pytest
from app.routes import reset as routes


@pytest.fixture
def reset_client(client, monkeypatch):
    with client.session_transaction() as state:
        state.update(authenticated=True, pin_verified=True, csrf_token="test-csrf", reset_session="test-session")
    routes._pending.clear()
    routes._locks.clear()
    monkeypatch.setattr(routes, "target", lambda server_id: ({"id": server_id, "name": "Test", "ip_address": "192.0.2.1"}, {"ip": "192.0.2.1", "port": 22, "user": "root", "password": "fixture-only"}))
    return client


def post(client, endpoint, body, server="one"):
    return client.post(f"/api/servers/{server}/reset/{endpoint}", json=body, headers={"X-CSRF-Token": "test-csrf"})


def make_plan(monkeypatch, client, blockers=None):
    plan = {"hostname": "test-vps", "plan_hash": "a" * 64, "blockers": blockers or [],
            "units": [], "paths": [], "containers": [], "volumes": [], "preserved": []}
    monkeypatch.setattr(routes, "remote", lambda *args: plan)
    response = post(client, "plan", {"components": ["bot"]})
    assert response.status_code == 200
    return response.get_json()["ticket"]


def test_reset_requires_login(client):
    assert post(client, "apply", {}).status_code == 401


def test_reset_requires_csrf(reset_client):
    assert reset_client.post("/api/servers/one/reset/plan", json={"components": ["bot"]}).status_code == 403


def test_reset_rejects_unknown_components(reset_client):
    assert post(reset_client, "plan", {"components": ["ssh"]}).status_code == 400


def test_reset_page_renders(reset_client):
    response = reset_client.get("/servers/one/reset")
    assert response.status_code == 200
    assert b'apply-reset' in response.data


def test_reset_wrong_hostname_never_runs(reset_client, monkeypatch):
    ticket = make_plan(monkeypatch, reset_client)
    run = MagicMock()
    monkeypatch.setattr(routes, "remote", run)
    assert post(reset_client, "apply", {"ticket": ticket, "confirmation": "production"}).status_code == 400
    run.assert_not_called()


def test_reset_blocked_plan_never_runs(reset_client, monkeypatch):
    ticket = make_plan(monkeypatch, reset_client, ["shared volume"])
    run = MagicMock()
    monkeypatch.setattr(routes, "remote", run)
    assert post(reset_client, "apply", {"ticket": ticket, "confirmation": "test-vps"}).status_code == 400
    run.assert_not_called()


def test_reset_ticket_is_server_bound(reset_client, monkeypatch):
    ticket = make_plan(monkeypatch, reset_client)
    assert post(reset_client, "apply", {"ticket": ticket, "confirmation": "test-vps"}, server="two").status_code == 409


def test_reset_ticket_expires(reset_client, monkeypatch):
    ticket = make_plan(monkeypatch, reset_client)
    routes._pending[ticket]["time"] = time.monotonic() - 601
    assert post(reset_client, "apply", {"ticket": ticket, "confirmation": "test-vps"}).status_code == 409


def test_reset_execute_once_and_only_audited_args(reset_client, monkeypatch):
    ticket = make_plan(monkeypatch, reset_client)
    run = MagicMock(return_value={"success": True, "backup": "/var/backups/test"})
    monkeypatch.setattr(routes, "remote", run)
    body = {"ticket": ticket, "confirmation": "test-vps", "components": ["vless"]}
    assert post(reset_client, "apply", body).status_code == 200
    assert run.call_args.args[1] == ["--components", "bot", "--apply", "--plan-hash", "a" * 64, "--confirm", "test-vps"]
    assert post(reset_client, "apply", body).status_code == 409
    assert run.call_count == 1


def test_reset_unknown_result_cannot_replay(reset_client, monkeypatch):
    ticket = make_plan(monkeypatch, reset_client)
    monkeypatch.setattr(routes, "remote", MagicMock(side_effect=TimeoutError))
    body = {"ticket": ticket, "confirmation": "test-vps"}
    assert post(reset_client, "apply", body).status_code == 502
    assert post(reset_client, "apply", body).status_code == 409


def test_remote_verifies_host_keys_and_sends_script_on_stdin(monkeypatch):
    client = MagicMock()
    stdin, stdout, stderr = MagicMock(), MagicMock(), MagicMock()
    stdout.read.return_value = b'{"success": true}'
    stdout.channel.recv_exit_status.return_value = 0
    client.exec_command.return_value = stdin, stdout, stderr
    monkeypatch.setattr(routes.paramiko, "SSHClient", lambda: client)
    routes.remote({"ip": "192.0.2.1", "port": 22, "user": "root", "password": "fixture-only"}, ["--components", "bot"])
    client.load_system_host_keys.assert_called_once()
    assert isinstance(client.set_missing_host_key_policy.call_args.args[0], paramiko.RejectPolicy)
    assert "fixture-only" not in client.exec_command.call_args.args[0]
    assert stdin.write.call_args.args[0] == routes.SCRIPT_SOURCE
    client.close.assert_called_once()
