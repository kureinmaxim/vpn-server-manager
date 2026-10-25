import re
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


def test_settings_getme_checkbox(app, client):
    from app.services.bot_stats import load_getme
    login(client)
    form = {"csrf_token": "token", "name": ["News bot"], "units": ["newsbot"], "containers": [""],
            "processes": [""], "health_url": [""], "health_word": [""], "role": ["bot"]}
    assert 'name="getme" value="1" id="bots-getme" checked' in client.get("/settings/bots").get_data(as_text=True)
    client.post("/settings/bots", data=form)
    assert load_getme(app) is False
    assert 'id="bots-getme" checked' not in client.get("/settings/bots").get_data(as_text=True)
    client.post("/settings/bots", data=dict(form, getme="1"))
    assert load_getme(app) is True


def test_modal_has_senders_section_in_english(app, client, all_features):
    login(client)
    html = client.get("/?lang=en").get_data(as_text=True)
    assert 'id="bots-check-senders"' in html and "Sending-only bots (no process)" in html
    assert "Tokens never leave the servers" in html


def test_settings_save_command_bot(app, client):
    login(client)
    form = {"csrf_token": "token", "name": ["Hermes"], "units": [""], "containers": [""], "processes": [""],
            "commands": ["hermes gateway run"], "tasks": ["lesson-report, lesson-report-test"],
            "health_url": [""], "health_word": [""], "role": ["bot"]}
    assert client.post("/settings/bots", data=form).status_code == 302
    [bot] = load_bots(app)
    assert bot["commands"] == ["hermes gateway run"] and bot["tasks"] == ["lesson-report", "lesson-report-test"]
    html = client.get("/settings/bots").get_data(as_text=True)
    assert 'value="hermes gateway run"' in html and 'value="lesson-report, lesson-report-test"' in html
    bad = client.post("/settings/bots", data=dict(form, commands=["x; reboot"]))
    assert bad.status_code == 400


def test_local_check_route(app, client, monkeypatch):
    import app.services.bot_stats as bot_stats
    assert client.get("/api/monitoring/bots/local").status_code == 401
    login(client)
    monkeypatch.setattr(bot_stats, "run_local", lambda bots, getme: {"node": {}, "bots": [], "senders": []})
    response = client.get("/api/monitoring/bots/local")
    assert response.status_code == 200 and response.headers["Cache-Control"] == "no-store"
    assert response.get_json()["stats"]["bots"] == [] and response.get_json()["name"]

    def broken(bots, getme):
        raise OSError("/Users/secret path")
    monkeypatch.setattr(bot_stats, "run_local", broken)
    failed = client.get("/api/monitoring/bots/local")
    assert failed.status_code == 502 and "secret" not in failed.get_data(as_text=True)


def test_settings_csrf_required(app, client):
    login(client)
    client.post("/settings/bots", data={"name": ["X"], "units": ["x"], "containers": [""], "processes": [""],
                                        "health_url": [""], "health_word": [""], "role": ["bot"]})
    assert "X" not in [b["name"] for b in load_bots(app)]


def test_index_has_bots_button_and_modal(app, client, all_features):
    login(client)
    html = client.get("/").get_data(as_text=True)
    assert 'data-bs-target="#botsCheckModal"' in html and 'bi-robot' in html
    assert "BOTS_CHECK_CONFIG" in html and "bots_check.js" in html


def test_modal_is_translated_to_english(app, client, all_features):
    login(client)
    html = client.get("/?lang=en").get_data(as_text=True)
    assert "Telegram bots on nodes" in html and ">Bots<" in html.replace(" ", "").replace("</i>", ">")
    assert "Telegram-боты на узлах" not in html


def test_snapshot_uses_first_answering_extra_address(bots_client, monkeypatch):
    from app.services import ssh_address
    ssh_address.forget()
    servers = registry.get("data_manager").load_servers.return_value
    servers[1]["extra_addresses"] = [{"address": "192.168.1.223", "label": "lan"}]
    monkeypatch.setattr(ssh_address, "_reachable", lambda address, port, timeout: address == "192.168.1.223")
    assert bots_client.get("/api/monitoring/nas/bots-snapshot").status_code == 200
    assert registry.get("ssh").get_bots_snapshot.call_args.kwargs["ip"] == "192.168.1.223"
    inventory = bots_client.get("/api/monitoring/load-check/servers").json["servers"]
    assert inventory[1]["addresses"] == ["198.51.100.6", "192.168.1.223"]
    ssh_address.forget()


def test_edit_form_saves_extra_addresses_and_drops_invalid(app, client):
    import os
    import re
    import tempfile
    from cryptography.fernet import Fernet
    from app.services.data_manager_service import DataManagerService
    login(client)
    folder = tempfile.mkdtemp()
    manager = DataManagerService(Fernet.generate_key().decode(), folder)
    path = os.path.join(folder, "servers.json.enc")
    app.config["active_data_file"] = path
    manager.save_servers([{"id": 1, "name": "tnas", "ip_address": "100.64.0.12", "kind": "nas",
                           "ssh_credentials": {"user": "mxm", "port": 9222}}], path)
    registry.register("data_manager", manager)
    page = client.get("/edit_server/1").get_data(as_text=True)
    assert page.count('name="extra_address"') == 2
    form = dict(re.findall(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', page))
    form.update(name="tnas", ip_address="100.64.0.12", kind="nas", ssh_user="mxm", ssh_port="9222",
                extra_address=["192.168.1.222", "bad; host"], extra_label=["lan", "direct"])
    response = client.post("/edit_server/1", data=form)
    assert response.status_code == 302
    with client.session_transaction() as session:
        categories = [category for category, _ in session.get("_flashes", [])]
    assert "warning" in categories
    assert manager.load_servers(app.config)[0]["extra_addresses"] == [{"address": "192.168.1.222", "label": "lan"}]
    html = client.get("/").get_data(as_text=True)
    assert 'data-ips="100.64.0.12 192.168.1.222"' in html


@pytest.mark.parametrize("kind,hidden", [("nas", True), ("pc", True), ("vps", False)])
def test_edit_form_hides_vps_only_sections_for_nas_and_pc(app, client, kind, hidden):
    login(client)
    manager = Mock()
    manager.load_servers.return_value = [{
        "id": 1, "name": "node", "ip_address": "192.0.2.5", "kind": kind, "specs": {}, "payment_info": {},
        "ssh_credentials": {"user": "mxm", "port": 9222, "key_hint": "ssh-ed25519 SHA256:abc", "key_path": "~/.ssh/k"},
        "panel_credentials": {}, "hoster_credentials": {}, "checks": {}}]
    registry.register("data_manager", manager)
    html = client.get("/edit_server/1").get_data(as_text=True)
    blocks = re.findall(r'data-node-kinds="vps"( hidden)?', html)
    assert len(blocks) == 4 and all(bool(b) == hidden for b in blocks)
    assert "node_kind.js" in html
    assert "SSH key saved" in html and "Replace SSH key" in html


@pytest.mark.parametrize("ssh,command,hint", [
    ({"user": "mxm", "port": 9222, "key_hint": "ssh-ed25519 SHA256:abc", "key_path": "~/.ssh/id_ed25519_maximkurein"},
     "ssh -i ~/.ssh/id_ed25519_maximkurein -p 9222 mxm@100.64.0.6", "no password needed"),
    ({"user": "mxm", "port": 9222, "key_hint": "ssh-ed25519 SHA256:abc", "key_path": "~/My Keys/nas"},
     'ssh -i &#34;$HOME/My Keys/nas&#34; -p 9222 mxm@100.64.0.6', "no password needed"),
    ({"user": "mxm", "port": 9222, "key_hint": "ssh-ed25519 SHA256:abc", "key_path": ""},
     "ssh -p 9222 mxm@100.64.0.6", "saved in the card as text"),
    ({"user": "root", "port": 22}, "ssh -p 22 root@100.64.0.6", "Login password"),
])
def test_card_ssh_command_uses_saved_key_path(app, client, ssh, command, hint):
    import os
    import tempfile
    from cryptography.fernet import Fernet
    from app.services.data_manager_service import DataManagerService
    login(client)
    folder = tempfile.mkdtemp()
    manager = DataManagerService(Fernet.generate_key().decode(), folder)
    path = os.path.join(folder, "servers.json.enc")
    app.config["active_data_file"] = path
    manager.save_servers([{"id": 1, "name": "tnas2", "ip_address": "100.64.0.6", "kind": "nas",
                           "ssh_credentials": ssh}], path)
    registry.register("data_manager", manager)
    html = client.get("/?lang=en").get_data(as_text=True)
    assert command in html and hint in html
