import json
import re
import socket
from unittest.mock import Mock

import pytest
from paramiko.ssh_exception import AuthenticationException, NoValidConnectionsError, SSHException

from app.routes.api import load_check_limiter
from app.services import registry
from app.services.load_snapshot import parse_snapshot
from tests.test_services.test_load_snapshot import SAMPLE


@pytest.fixture
def load_client(client):
    with client.session_transaction() as session:
        session.update(authenticated=True, pin_verified=True, language="ru")
    servers = [
        {
            "id": "one",
            "name": "Active server",
            "ip_address": "192.0.2.1",
            "status": "Active",
            "ssh_credentials": {"user": "admin", "port": 2222, "password": "encrypted"},
        },
        {"id": "archived", "status": "Active", "archived": True},
        {"id": "inactive", "status": "Inactive"},
        {"id": "suspended", "status": "Suspended"},
        {"id": "legacy", "ip_address": "192.0.2.2"},
    ]
    manager = Mock()
    manager.load_servers.return_value = servers
    manager.decrypt_data.return_value = "decrypted-secret"
    registry.register("data_manager", manager)
    ssh = Mock()
    ssh.get_load_snapshot.return_value = parse_snapshot(SAMPLE)
    registry.register("ssh", ssh)
    load_check_limiter.requests.clear()
    yield client
    load_check_limiter.requests.clear()


@pytest.mark.parametrize(
    "url", ["/api/monitoring/load-check/servers", "/api/monitoring/one/load-snapshot", "/api/monitoring/load-check/mesh",
            "/api/monitoring/load-check/derp", "/api/monitoring/one/derp-snapshot", "/api/monitoring/load-check/peer-path/demo"]
)
def test_load_check_requires_auth_and_pin(client, url):
    assert client.get(url).status_code == 401
    with client.session_transaction() as session:
        session["authenticated"] = True
    assert client.get(url).status_code == 401


def test_inventory_filters_inactive_and_archived_without_exposing_secrets(load_client):
    response = load_client.get("/api/monitoring/load-check/servers")
    assert response.status_code == 200
    assert [server["id"] for server in response.json["servers"]] == ["one", "legacy"]
    assert set(response.json["servers"][0]) == {"id", "name", "ip_address", "kind", "addresses"}
    assert response.headers["Cache-Control"] == "no-store"
    registry.get("ssh").get_load_snapshot.assert_not_called()


def test_inventory_kind_filter_keeps_nas_out_of_server_load(load_client):
    servers = registry.get("data_manager").load_servers.return_value
    servers.append({"id": "nas", "name": "tnas2", "ip_address": "198.51.100.6", "kind": "nas"})
    every = load_client.get("/api/monitoring/load-check/servers").json["servers"]
    assert [(s["id"], s["kind"]) for s in every] == [("one", "vps"), ("legacy", "vps"), ("nas", "nas")]
    vps = load_client.get("/api/monitoring/load-check/servers?kind=vps").json["servers"]
    assert [s["id"] for s in vps] == ["one", "legacy"]


def test_mesh_context_is_local_and_not_cached(load_client, monkeypatch):
    from app.services import mesh_context
    monkeypatch.setattr(mesh_context, 'local_mesh', lambda: {'state':'ready','nodes':[],'host':'test-pc'})
    response = load_client.get('/api/monitoring/load-check/mesh')
    assert response.json['host'] == 'test-pc'
    assert response.headers['Cache-Control'] == 'no-store'
    registry.get('ssh').get_load_snapshot.assert_not_called()


def test_snapshot_uses_saved_ssh_credentials(load_client):
    response = load_client.get("/api/monitoring/one/load-snapshot")
    assert response.status_code == 200
    assert response.json["stats"]["cpu"]["used_pct"] == 50
    registry.get("ssh").get_load_snapshot.assert_called_once_with(
        ip="192.0.2.1", user="admin", port=2222, password="decrypted-secret"
    )
    assert b"secret" not in response.data
    assert response.headers["Cache-Control"] == "no-store"


def test_derp_endpoints_are_separate_from_load(load_client, monkeypatch):
    from app.services import derp_context
    monkeypatch.setattr(derp_context, 'local_derp', lambda: {'state': 'ready', 'regions': []})
    response = load_client.get('/api/monitoring/load-check/derp')
    assert response.status_code == 200 and response.headers['Cache-Control'] == 'no-store'
    ssh = registry.get('ssh')
    ssh.get_derp_snapshot.return_value = {'state': 'ready', 'probe_code': 200}
    for _ in range(6):
        response = load_client.get('/api/monitoring/one/derp-snapshot')
        assert response.status_code == 200 and response.json['stats']['probe_code'] == 200
    assert load_client.get('/api/monitoring/one/derp-snapshot').status_code == 429
    assert load_client.get('/api/monitoring/one/load-snapshot').status_code == 200
    assert load_client.get('/api/monitoring/archived/derp-snapshot').status_code == 409
    ssh.get_derp_snapshot.assert_called_with(ip='192.0.2.1', user='admin', password='decrypted-secret', port=2222)


@pytest.mark.parametrize(
    "server_id,status",
    [
        ("archived", 409),
        ("inactive", 409),
        ("suspended", 409),
        ("legacy", 400),
        ("missing", 404),
    ],
)
def test_skip_unavailable_or_no_longer_active_servers(load_client, server_id, status):
    assert (
        load_client.get(f"/api/monitoring/{server_id}/load-snapshot").status_code
        == status
    )
    registry.get("ssh").get_load_snapshot.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("private-secret"),
        AuthenticationException("private-secret"),
        ValueError("private-secret"),
    ],
)
def test_failure_isolated_and_does_not_leak_details(load_client, error):
    registry.get("ssh").get_load_snapshot.side_effect = [error, parse_snapshot(SAMPLE)]
    response = load_client.get("/api/monitoring/one/load-snapshot")
    assert response.status_code == 502
    assert "error" in response.json
    assert b"private-secret" not in response.data
    assert load_client.get("/api/monitoring/one/load-snapshot").status_code == 200


@pytest.mark.parametrize(
    "error, text",
    [
        (ConnectionRefusedError("private-secret"), "порт SSH закрыт"),
        (socket.gaierror("private-secret"), "найти адрес"),
        (TimeoutError("private-secret"), "за отведённое время"),
        (SSHException("private-secret"), "сессия не открылась"),
        (NoValidConnectionsError({("192.0.2.1", 22): ConnectionRefusedError()}), "порт SSH закрыт"),
        (AuthenticationException("private-secret"), "логин и пароль"),
        (RuntimeError("private-secret"), "Сервер не ответил."),
    ],
)
def test_failure_reason_is_specific_without_details(load_client, error, text):
    registry.get("ssh").get_load_snapshot.side_effect = [error]
    response = load_client.get("/api/monitoring/one/load-snapshot")
    assert response.status_code == 502
    assert text in response.json["error"]
    assert b"private-secret" not in response.data


def test_repeated_snapshots_are_rate_limited(load_client):
    for _ in range(6):
        assert load_client.get("/api/monitoring/one/load-snapshot").status_code == 200
    assert load_client.get("/api/monitoring/one/load-snapshot").status_code == 429
    assert registry.get("ssh").get_load_snapshot.call_count == 6


def test_empty_inventory(load_client):
    registry.get("data_manager").load_servers.return_value = []
    assert load_client.get("/api/monitoring/load-check/servers").json == {"servers": []}


def test_main_page_includes_load_check_in_offline_mode(load_client, all_features):
    registry.get("data_manager").load_servers.return_value = []
    response = load_client.get("/")
    assert response.status_code == 200
    assert b'data-bs-target="#loadCheckModal"' in response.data
    assert b"js/load_check.js" in response.data
    assert b'data-bs-target="#projectsCheckModal"' in response.data
    assert b"js/projects_check.js" in response.data and b"BotCriptoM" not in response.data
    assert "Chatmail relay" in response.get_data(as_text=True)
    assert "Свой DERP" in response.get_data(as_text=True) or "Custom DERP" in response.get_data(as_text=True)
    assert "rnsd" not in response.get_data(as_text=True)


def test_projects_snapshot_uses_saved_credentials_and_own_rate_limit(load_client):
    ssh = registry.get("ssh")
    ssh.get_projects_snapshot.return_value = [{"key": "botcriptom", "name": "BotCriptoM", "state": "running", "components": []}]
    assert client_get_ok(load_client, "/api/monitoring/one/load-snapshot")
    response = load_client.get("/api/monitoring/one/projects-snapshot")
    assert response.status_code == 200 and response.json["stats"][0]["name"] == "BotCriptoM"
    assert response.headers["Cache-Control"] == "no-store"
    ssh.get_projects_snapshot.assert_called_once_with(
        ip="192.0.2.1", user="admin", port=2222, password="decrypted-secret"
    )
    assert load_client.get("/api/monitoring/archived/projects-snapshot").status_code == 409
    for _ in range(5):
        load_client.get("/api/monitoring/one/projects-snapshot")
    assert load_client.get("/api/monitoring/one/projects-snapshot").status_code == 429
    with load_client.application.test_client() as anonymous:
        assert anonymous.get("/api/monitoring/one/projects-snapshot").status_code == 401


def test_roles_snapshot_returns_own_dns_and_chatmail_roles(load_client):
    ssh = registry.get("ssh")
    ssh.get_roles_snapshot.return_value = [{"key": "adguard", "name": "AdGuard Home / DNS", "state": "running", "components": []}]
    response = load_client.get("/api/monitoring/one/roles-snapshot")
    assert response.status_code == 200 and response.json["stats"][0]["key"] == "adguard"
    ssh.get_roles_snapshot.assert_called_once_with(
        ip="192.0.2.1", user="admin", port=2222, password="decrypted-secret"
    )
    assert load_client.get("/api/monitoring/archived/roles-snapshot").status_code == 409
    response = load_client.get("/")
    assert b"roles-snapshot" in response.data


def client_get_ok(client, url):
    return client.get(url).status_code == 200


def test_load_check_follows_language_switch_for_labels_units_and_api(load_client):
    manager = registry.get("data_manager")
    servers = manager.load_servers.return_value
    registry.get("ssh").get_load_snapshot.side_effect = TimeoutError()
    locales = {
        "ru": ("Загрузка серверов", "Обновить", "ЦП", "ГиБ", "/с", "Нет данных"),
        "en": ("Server load", "Refresh", "CPU", "GiB", "/s", "No data"),
        "zh": ("服务器负载", "刷新", "处理器", "GiB", "/秒", "无数据"),
    }
    # Reuse one session to catch stale translations after changing language.
    for language in ("en", "ru", "zh", "en"):
        # The shared app fixture keeps g alive; real requests use fresh contexts.
        with load_client.application.app_context():
            title, refresh, cpu, unit, per_second, failed = locales[language]
            assert load_client.get(f"/change_language/{language}").status_code == 302
            manager.load_servers.return_value = []
            html = load_client.get("/").get_data(as_text=True)
            assert f'lang="{language}"' in html
            assert f'data-bs-target="#loadCheckModal"' in html
            modal = html.split('id="loadCheckModal"', 1)[1].split("<script>", 1)[0]
            assert title in modal and refresh in modal and f"{cpu} ↕" in modal
            script = html.split("window.LOAD_CHECK_CONFIG =", 1)[1].split(
                "</script>", 1
            )[0]
            strings = [
                json.loads(value) for value in re.findall(r'"(?:\\.|[^"\\])*"', script)
            ]
            assert unit in strings and per_second in strings and failed in strings
            manager.load_servers.return_value = servers
            response = load_client.get("/api/monitoring/one/load-snapshot")
            assert response.status_code == 502
            if language == "ru":
                assert "Сервер не ответил" in response.json["error"]
            else:
                assert not re.search(
                    r"[А-Яа-яЁё]", modal + "".join(strings) + response.json["error"]
                )
