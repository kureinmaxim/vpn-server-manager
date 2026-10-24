from unittest.mock import Mock

import pytest

from app.routes.api import load_check_limiter
from app.services import registry
from app.services.bot_stats import DEFAULT_BOTS, clean_bots, load_bots, parse
from tests.test_services.test_bot_stats import ULTRAHOST


@pytest.fixture
def bots_client(client):
    with client.session_transaction() as session:
        session.update(authenticated=True, pin_verified=True, language="ru")
    manager = Mock()
    manager.load_servers.return_value = [
        {"id": "vps", "name": "UltraHost", "ip_address": "192.0.2.11", "status": "Active",
         "ssh_credentials": {"user": "root", "port": 22, "password": "encrypted"}},
        {"id": "nas", "name": "tnas2", "ip_address": "198.51.100.6", "status": "Active", "kind": "nas",
         "ssh_credentials": {"user": "mxm", "port": 9222, "private_key": "encrypted-key"}},
    ]
    manager.decrypt_data.return_value = "decrypted-secret"
    registry.register("data_manager", manager)
    ssh = Mock()
    ssh.get_bots_snapshot.return_value = parse(ULTRAHOST, clean_bots(DEFAULT_BOTS))
    registry.register("ssh", ssh)
    load_check_limiter.requests.clear()
    yield client
    load_check_limiter.requests.clear()


@pytest.mark.parametrize("url", ["/api/monitoring/vps/bots-snapshot", "/api/monitoring/bots/mesh-only"])
def test_bots_routes_require_auth_and_pin(client, url):
    assert client.get(url).status_code == 401
    with client.session_transaction() as session:
        session["authenticated"] = True
    assert client.get(url).status_code == 401


def test_snapshot_uses_card_credentials_and_hides_secrets(bots_client):
    response = bots_client.get("/api/monitoring/vps/bots-snapshot")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json["stats"]["bots"][0]["name"] == "TelegramOnly"
    registry.get("ssh").get_bots_snapshot.assert_called_once_with(
        ip="192.0.2.11", user="root", port=22, password="decrypted-secret")
    body = response.get_data(as_text=True)
    for forbidden in ("decrypted-secret", "Environment", "SECRET", ".env"):
        assert forbidden not in body


def test_nas_card_is_polled_with_its_port_and_key(bots_client):
    assert bots_client.get("/api/monitoring/nas/bots-snapshot").status_code == 200
    registry.get("ssh").get_bots_snapshot.assert_called_once_with(
        ip="198.51.100.6", user="mxm", port=9222, password="", key="decrypted-secret", key_passphrase="")


def test_ssh_errors_are_generic(bots_client):
    registry.get("ssh").get_bots_snapshot.side_effect = OSError("connect to 192.0.2.11 failed: secret")
    response = bots_client.get("/api/monitoring/vps/bots-snapshot")
    assert response.status_code == 502
    assert "192.0.2.11" not in response.get_data(as_text=True)
    assert "secret" not in response.get_data(as_text=True)


def test_rate_limited(bots_client):
    codes = [bots_client.get("/api/monitoring/vps/bots-snapshot").status_code for _ in range(7)]
    assert codes[:6] == [200] * 6 and codes[6] == 429


def test_mesh_only_lists_peers_without_cards(bots_client, monkeypatch):
    from app.services import mesh_context
    monkeypatch.setattr(mesh_context, "local_mesh", lambda: {"state": "ready", "host": "mk", "nodes": [
        {"name": "mk", "ips": ["100.64.0.2"], "online": True},
        {"name": "tnas", "ips": ["100.64.0.12"], "online": False},
        {"name": "tnas2", "ips": ["198.51.100.6"], "online": True},
    ]})
    response = bots_client.get("/api/monitoring/bots/mesh-only")
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json["nodes"] == [
        {"name": "mk", "ip": "100.64.0.2", "online": True, "self": True},
        {"name": "tnas", "ip": "100.64.0.12", "online": False, "self": False}]
    registry.get("ssh").get_bots_snapshot.assert_not_called()


def login(client):
    with client.session_transaction() as session:
        session.update(authenticated=True, pin_authenticated=True, pin_verified=True, csrf_token="token")


def test_settings_page_lists_defaults_and_requires_login(app, client):
    assert client.get("/settings/bots").status_code in (302, 401)
    login(client)
    html = client.get("/settings/bots").get_data(as_text=True)
    assert 'value="TelegramOnly"' in html and 'value="http://127.0.0.1:8000/health"' in html
    assert 'value="telegram-helper-lite"' in html


def test_settings_save_reject_and_reset(app, client):
    login(client)
    form = {"csrf_token": "token", "name": ["News bot", "Nightly"], "units": ["newsbot", "nightly-job"],
            "containers": ["", ""], "processes": ["", ""], "health_url": ["", ""], "health_word": ["", ""],
            "role": ["bot", "service"]}
    assert client.post("/settings/bots", data=form).status_code == 302
    assert [(b["name"], b["service"]) for b in load_bots(app)] == [("News bot", False), ("Nightly", True)]
    bad = dict(form, units=["x; reboot", "nightly-job"])
    response = client.post("/settings/bots", data=bad)
    assert response.status_code == 400 and 'value="x; reboot"' in response.get_data(as_text=True)
    assert [b["name"] for b in load_bots(app)] == ["News bot", "Nightly"]
    client.post("/settings/bots", data={"csrf_token": "token", "action": "reset"})
    assert "TelegramOnly" in [b["name"] for b in load_bots(app)]


def test_settings_csrf_required(app, client):
    login(client)
    client.post("/settings/bots", data={"name": ["X"], "units": ["x"], "containers": [""], "processes": [""],
                                        "health_url": [""], "health_word": [""], "role": ["bot"]})
    assert "X" not in [b["name"] for b in load_bots(app)]


def test_index_has_bots_button_and_modal(app, client):
    login(client)
    html = client.get("/").get_data(as_text=True)
    assert 'data-bs-target="#botsCheckModal"' in html and 'bi-robot' in html
    assert "BOTS_CHECK_CONFIG" in html and "bots_check.js" in html


def test_modal_is_translated_to_english(app, client):
    login(client)
    html = client.get("/?lang=en").get_data(as_text=True)
    assert "Telegram bots on nodes" in html and ">Bots<" in html.replace(" ", "").replace("</i>", ">")
    assert "Telegram-боты на узлах" not in html
