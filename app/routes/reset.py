"""Explicit, CSRF-protected TelegramOnly reset, bound to an audited SSH host."""
import hmac
import json
import secrets
import shlex
import threading
import time

import paramiko
from flask import Blueprint, current_app, jsonify, render_template, request, session, abort

from ..services import registry
from ..services.reset_payload import SCRIPT_SOURCE
from ..utils.decorators import require_auth, require_pin, csrf_protect
from .api import _get_server_ssh_credentials

reset_bp = Blueprint("reset", __name__)
COMPONENTS = ("bot", "mieru", "naiveproxy", "hysteria2", "vless", "mtproto", "ha")
_pending = {}
_locks = {}
_guard = threading.Lock()
TTL = 600


def target(server_id):
    manager = registry.get("data_manager")
    if not manager:
        abort(503)
    server, creds = _get_server_ssh_credentials(server_id, manager)
    if not server or not creds:
        abort(404)
    return server, creds


def identity(creds):
    return (creds["ip"], int(creds["port"]), creds["user"])


def remote(creds, args):
    # WARNING: The general SSH pool accepts unknown host keys. Destructive reset
    # must use verified OpenSSH known_hosts and RejectPolicy instead.
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        client.connect(hostname=creds["ip"], port=int(creds["port"]), username=creds["user"],
                       password=creds["password"] or None, timeout=20,
                       auth_timeout=20, banner_timeout=20)
        command = ([] if creds["user"] == "root" else ["sudo", "-n"]) + ["python3", "-", *args]
        stdin, stdout, stderr = client.exec_command(shlex.join(command), timeout=1800)
        stdin.write(SCRIPT_SOURCE)
        stdin.flush()
        stdin.channel.shutdown_write()
        raw = stdout.read(2 * 1024 * 1024)
        status = stdout.channel.recv_exit_status()
        # Never return SSH exceptions or arbitrary remote stderr to the UI/log.
        result = json.loads(raw.decode("utf-8"))
        if not isinstance(result, dict):
            raise ValueError("Invalid reset response")
        if status and "plan_hash" not in result:
            return {"success": False, "error": result.get("error", "Remote reset failed"), "backup": result.get("backup")}
        return result
    finally:
        client.close()


@reset_bp.route("/servers/<server_id>/reset")
@require_auth
@require_pin
def reset_page(server_id):
    server, _ = target(server_id)
    session.setdefault("csrf_token", secrets.token_urlsafe(32))
    session.setdefault("reset_session", secrets.token_urlsafe(32))
    return render_template("reset.html", server=server, components=COMPONENTS)


@reset_bp.route("/api/servers/<server_id>/reset/plan", methods=["POST"])
@require_auth
@require_pin
@csrf_protect
def reset_plan(server_id):
    body = request.get_json(silent=True) or {}
    components = body.get("components")
    if not isinstance(components, list) or not components or any(not isinstance(c, str) or c not in COMPONENTS for c in components):
        return jsonify(error="Выберите компоненты из списка"), 400
    _, creds = target(server_id)
    components = sorted(set(components))
    try:
        plan = remote(creds, ["--components", ",".join(components)])
    except Exception:
        return jsonify(error="Аудит не выполнен. Проверьте SSH, known_hosts и root/sudo -n. Ничего не удалено."), 502
    if "plan_hash" not in plan:
        return jsonify(error=plan.get("error", "Аудит не выполнен")), 409
    ticket = secrets.token_urlsafe(32)
    owner = session.setdefault("reset_session", secrets.token_urlsafe(32))
    with _guard:
        now = time.monotonic()
        for key, item in list(_pending.items()):
            if now - item["time"] > TTL or (item["owner"] == owner and item["server"] == server_id):
                _pending.pop(key, None)
        _pending[ticket] = {"owner": owner, "server": server_id, "identity": identity(creds),
                            "components": components, "plan": plan, "time": now}
    return jsonify(plan=plan, ticket=ticket, expires_in=TTL)


@reset_bp.route("/api/servers/<server_id>/reset/apply", methods=["POST"])
@require_auth
@require_pin
@csrf_protect
def reset_apply(server_id):
    body = request.get_json(silent=True) or {}
    ticket = body.get("ticket")
    if not isinstance(ticket, str):
        return jsonify(error="Сначала получите план очистки"), 400
    _, creds = target(server_id)
    with _guard:
        item = _pending.get(ticket)
        if (not item or item["server"] != server_id or item["identity"] != identity(creds)
                or not hmac.compare_digest(item["owner"], session.get("reset_session", ""))
                or time.monotonic() - item["time"] > TTL):
            return jsonify(error="План устарел или относится к другому серверу/сеансу"), 409
        plan = item["plan"]
        if plan.get("blockers") or body.get("confirmation") != plan["hostname"]:
            return jsonify(error="Устраните блокировки и введите точное имя сервера"), 400
        lock = _locks.setdefault(identity(creds)[:2], threading.Lock())
        if not lock.acquire(blocking=False):
            return jsonify(error="Очистка этого сервера уже выполняется"), 409
        # Consume before SSH: an uncertain response must not cause a destructive retry.
        _pending.pop(ticket)
    try:
        result = remote(creds, ["--components", ",".join(item["components"]), "--apply",
                                "--plan-hash", plan["plan_hash"], "--confirm", plan["hostname"]])
        return jsonify(result), (200 if result.get("success") else 409)
    except Exception:
        return jsonify(error="Ответ потерян или выполнение прервано. Не повторяйте автоматически: проверьте Status и /var/backups/telegramonly-reset по SSH."), 502
    finally:
        lock.release()
