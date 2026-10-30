"""Explicit, CSRF-protected TelegramOnly reset, bound to an audited SSH host."""
import hmac
import json
import logging
import os
import secrets
import shlex
import socket
import threading
import time

import paramiko
from flask_babel import gettext as translate
from flask import Blueprint, current_app, jsonify, render_template, request, session, abort

from ..services import registry
from ..services.reset_payload import SCRIPT_SOURCE
from ..services.ssh_auth import connect_kwargs, has_ssh_auth
from ..utils.decorators import require_auth, require_pin, csrf_protect
from .api import _get_server_ssh_credentials

reset_bp = Blueprint("reset", __name__)
logger = logging.getLogger(__name__)
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


from ..services.ssh_trust import UnknownHostKeyError, RejectUnknownHost, load_known_hosts, host_key_message


class RemoteConnectError(Exception):
    """Подключение не удалось — команда на сервере не запускалась."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class RemoteOutputError(ValueError):
    """Команда запустилась, но ответ не получен или не разобран (см. reason)."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _connect(client, creds):
    try:
        # Вход как у мониторинга: пароль и/или ключ из карточки. ~/.ssh и ssh-agent —
        # только если в карточке нет ни того, ни другого: иначе чужие ключи агента
        # исчерпают MaxAuthTries раньше пароля (Too many authentication failures).
        from ..services.ssh_service import SSHService
        SSHService.connect_managed(client, hostname=creds["ip"], port=int(creds["port"]), username=creds["user"],
                       timeout=20, auth_timeout=20, banner_timeout=20,
                       **connect_kwargs(creds.get("password"), creds.get("key"), creds.get("key_passphrase"),
                                        use_local_keys=not has_ssh_auth(creds)))
    except UnknownHostKeyError as exc:
        raise RemoteConnectError("unknown_host") from exc
    except paramiko.BadHostKeyException as exc:
        raise RemoteConnectError("changed_host") from exc
    except paramiko.AuthenticationException as exc:
        raise RemoteConnectError("auth") from exc
    except (socket.timeout, TimeoutError) as exc:
        raise RemoteConnectError("timeout") from exc
    except (OSError, paramiko.SSHException) as exc:
        raise RemoteConnectError("unreachable") from exc


def describe_failure(exc, creds, *, may_have_run=False):
    """Понятная причина сбоя remote() или None (тогда показывается общий текст).

    may_have_run=True — операция с изменениями: после запуска команды точная причина
    неизвестна, поэтому называются только отказы до подключения. Текст исключений
    paramiko и stderr сервера не показываются и не пишутся в журнал.
    """
    trust_message = host_key_message(exc)
    if trust_message:
        return trust_message
    reason = getattr(exc, "reason", None)
    logger.warning("SSH remote operation failed: %s (%s)", reason or "unknown", type(exc).__name__)
    ip, port, user = creds.get("ip"), creds.get("port", 22), creds.get("user", "root")
    if isinstance(exc, RemoteConnectError):
        endpoint = ip if int(port) == 22 else f'[{ip}]:{port}'
        if reason == "unknown_host":
            return host_key_message(UnknownHostKeyError(endpoint))
        if reason == "changed_host":
            return host_key_message(paramiko.BadHostKeyException(endpoint, None, None))
        if reason == "auth":
            return translate("SSH: не удалось войти. Проверьте пароль или SSH-ключ в карточке сервера.")
        if reason == "timeout":
            return translate("Время ожидания SSH-соединения истекло до входа. Проверьте адрес, порт и сетевой маршрут.")
        return translate("Сервер не ответил по SSH. Проверьте IP, порт %(port)s и доступность сервера.", port=port)
    if isinstance(exc, RemoteOutputError) and reason == "unsupported_platform":
        return translate("Эта операция поддерживает только Debian или Ubuntu Linux. Изменений не внесено.")
    if isinstance(exc, RemoteOutputError) and reason in ("privilege", "sudo_missing", "sudo_password"):
        if reason == "sudo_missing":
            return translate("На удалённом узле нет sudo. Для этой операции нужен root или установленный sudo.")
        if reason == "privilege":
            return translate("У пользователя SSH недостаточно прав. Используйте root или настройте sudo без запроса пароля.")
        return translate("sudo запрашивает пароль. Подключайтесь как root или разрешите пользователю sudo без пароля.")
    if isinstance(exc, RemoteOutputError) and not may_have_run:
        if exc.reason == "no_python":
            return translate("На сервере нет python3 — он нужен для этой операции: apt-get install -y python3")
        if exc.reason == "python_error":
            return translate("python3 на сервере завершился с ошибкой — возможно, версия старше 3.7. "
                             "Проверьте: ssh -p %(port)s %(user)s@%(ip)s python3 --version", port=port, user=user, ip=ip)
        if exc.reason == "bad_output":
            return translate("Сервер ответил не в ожидаемом формате. Проверьте, что вход по SSH ничего не печатает "
                             "и не запускает программ: ssh -p %(port)s %(user)s@%(ip)s true — не должна ничего выводить "
                             "(см. ~/.bashrc и ~/.profile на сервере).", port=port, user=user, ip=ip)
        if exc.reason == "no_output":
            return translate("Сервер не вернул данных. Проверьте вручную: ssh -p %(port)s %(user)s@%(ip)s python3 --version",
                             port=port, user=user, ip=ip)
        if exc.reason == "exec_failed":
            return translate("Подключение есть, но выполнить команду не удалось: сервер закрыл канал SSH или не ответил вовремя.")
    return None


OUTPUT_MARKER = "__VSM_REMOTE_OUTPUT__"


def _load_known_hosts(client):
    load_known_hosts(client)


def failure_code(exc):
    """Имя типа исключения для общего сообщения — без текста исключения, только класс."""
    return f" ({type(exc).__name__})" if exc is not None else ""


def remote(creds, args, *, source=SCRIPT_SOURCE):
    # Dedicated connections use the same fail-closed trust loader as monitoring.
    client = paramiko.SSHClient()
    try:
        _load_known_hosts(client)
        client.set_missing_host_key_policy(RejectUnknownHost())
        _connect(client, creds)
        command = ([] if creds["user"] == "root" else ["sudo", "-n"]) + ["python3", "-", *args]
        # Метка отделяет ответ скрипта от того, что при входе печатают ~/.bashrc,
        # ~/.profile и скрипты входа: такой текст ломал разбор JSON.
        shell_command = f"printf '%s\\n' {OUTPUT_MARKER}; {shlex.join(command)}"
        try:
            stdin, stdout, stderr = client.exec_command(shell_command, timeout=1800)
            stdin.write(source)
            stdin.flush()
            stdin.channel.shutdown_write()
            raw = stdout.read(2 * 1024 * 1024)
            status = stdout.channel.recv_exit_status()
        except (OSError, paramiko.SSHException) as exc:
            raise RemoteOutputError("exec_failed") from exc
        text = raw.decode("utf-8", errors="replace")
        _, found, body = text.partition(OUTPUT_MARKER + "\n")
        if not found:
            body = text  # ответ без метки (старые сценарии, заглушки тестов)
        if not body.strip():
            # Ответа нет: по stderr определяется только причина, сам текст никуда не уходит.
            err = (stderr.read(4096) or b"").lower()
            if b"password is required" in err or b"terminal is required" in err:
                raise RemoteOutputError("sudo_password")
            if b"sudo" in err and b"not found" in err:
                raise RemoteOutputError("sudo_missing")
            if any(marker in err for marker in (b"not in the sudoers", b"not permitted")):
                raise RemoteOutputError("privilege")
            if b"sudo" in err and b"permission denied" in err:
                raise RemoteOutputError("privilege")
            if status == 127 or b"not found" in err:
                raise RemoteOutputError("no_python")
            if b"traceback" in err or b"syntaxerror" in err:
                raise RemoteOutputError("python_error")
            raise RemoteOutputError("no_output")
        # Never return SSH exceptions or arbitrary remote stderr to the UI/log.
        try:
            result = json.loads(body)
        except ValueError as exc:
            raise RemoteOutputError("bad_output") from exc
        if not isinstance(result, dict):
            raise ValueError("Invalid reset response")
        if status and "plan_hash" not in result:
            if result.get("error") == "Debian/Ubuntu Linux required":
                raise RemoteOutputError("unsupported_platform")
            if result.get("error") == "Run with sudo for a complete inventory":
                raise RemoteOutputError("privilege")
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
        return jsonify(error=translate("Выберите компоненты из списка")), 400
    _, creds = target(server_id)
    components = sorted(set(components))
    try:
        plan = remote(creds, ["--components", ",".join(components)])
    except Exception as exc:
        return jsonify(error=describe_failure(exc, creds) or translate("Аудит не выполнен. Проверьте SSH, known_hosts и root/sudo -n. Ничего не удалено.") + failure_code(exc)), 502
    if "plan_hash" not in plan:
        return jsonify(error=plan.get("error", translate("Аудит не выполнен"))), 409
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
        return jsonify(error=translate("Сначала получите план очистки")), 400
    _, creds = target(server_id)
    with _guard:
        item = _pending.get(ticket)
        if (not item or item["server"] != server_id or item["identity"] != identity(creds)
                or not hmac.compare_digest(item["owner"], session.get("reset_session", ""))
                or time.monotonic() - item["time"] > TTL):
            return jsonify(error=translate("План устарел или относится к другому серверу/сеансу")), 409
        plan = item["plan"]
        if plan.get("blockers") or body.get("confirmation") != plan["hostname"]:
            return jsonify(error=translate("Устраните блокировки и введите точное имя сервера")), 400
        lock = _locks.setdefault(identity(creds)[:2], threading.Lock())
        if not lock.acquire(blocking=False):
            return jsonify(error=translate("Очистка этого сервера уже выполняется")), 409
        # Consume before SSH: an uncertain response must not cause a destructive retry.
        _pending.pop(ticket)
    try:
        result = remote(creds, ["--components", ",".join(item["components"]), "--apply",
                                "--plan-hash", plan["plan_hash"], "--confirm", plan["hostname"]])
        return jsonify(result), (200 if result.get("success") else 409)
    except Exception as exc:
        return jsonify(error=describe_failure(exc, creds, may_have_run=True) or translate("Ответ потерян или выполнение прервано. Не повторяйте автоматически: проверьте Status и /var/backups/telegramonly-reset по SSH.") + failure_code(exc)), 502
    finally:
        lock.release()


_archive_tickets = {}


@reset_bp.route('/servers/<server_id>/reset/archives')
@require_auth
@require_pin
def archive_page(server_id):
    server, _ = target(server_id)
    session.setdefault('csrf_token', secrets.token_urlsafe(32))
    session.setdefault('reset_session', secrets.token_urlsafe(32))
    return render_template('reset_archives.html', server=server)


@reset_bp.route('/api/servers/<server_id>/reset/archives', methods=['POST'])
@require_auth
@require_pin
@csrf_protect
def archive_list(server_id):
    from ..services.archive_payload import ARCHIVE_SOURCE
    _, creds = target(server_id)
    try:
        result = remote(creds, [], source=ARCHIVE_SOURCE)
        if 'archives' not in result:
            return jsonify(error=translate('Не удалось прочитать архивы. Проверьте SSH и права доступа.')), 502
    except Exception as exc:
        return jsonify(error=describe_failure(exc, creds) or translate('Не удалось прочитать архивы. Проверьте SSH, known_hosts и права доступа.') + failure_code(exc)), 502
    owner = session.setdefault('reset_session', secrets.token_urlsafe(32))
    with _guard:
        now = time.monotonic()
        for key, item in list(_archive_tickets.items()):
            if now - item['time'] > TTL or (item['owner'] == owner and item['server'] == server_id):
                _archive_tickets.pop(key, None)
        for archive in result['archives']:
            token = secrets.token_urlsafe(32)
            _archive_tickets[token] = dict(owner=owner, server=server_id, identity=identity(creds),
                time=now, name=archive['name'], hash=archive.pop('hash'), hostname=result['hostname'])
            archive['ticket'] = token
    return jsonify(result)


@reset_bp.route('/api/servers/<server_id>/reset/archives/delete', methods=['POST'])
@require_auth
@require_pin
@csrf_protect
def archive_delete(server_id):
    from ..services.archive_payload import ARCHIVE_SOURCE
    body = request.get_json(silent=True) or {}
    token = body.get('ticket') if isinstance(body, dict) else None
    if not isinstance(token, str):
        return jsonify(error=translate('Сначала загрузите список архивов')), 400
    _, creds = target(server_id)
    with _guard:
        item = _archive_tickets.get(token)
        if (not item or item['server'] != server_id or item['identity'] != identity(creds)
                or item['owner'] != session.get('reset_session') or time.monotonic() - item['time'] > TTL):
            return jsonify(error=translate('Обновите список архивов')), 409
        if body.get('confirmation') != item['hostname']:
            return jsonify(error=translate('Введите точное имя VPS')), 400
        lock = _locks.setdefault(identity(creds)[:2], threading.Lock())
        if not lock.acquire(blocking=False):
            return jsonify(error=translate('Другая операция уже выполняется')), 409
        _archive_tickets.pop(token)
    try:
        result = remote(creds, [item['name'], item['hash'], item['hostname']], source=ARCHIVE_SOURCE)
        if result.get('error'):
            result['error'] = translate(result['error'])
        return jsonify(result), (200 if result.get('success') else 409)
    except Exception as exc:
        return jsonify(error=describe_failure(exc, creds, may_have_run=True) or translate('Ответ потерян. Обновите список перед дальнейшими действиями.') + failure_code(exc)), 502
    finally:
        lock.release()


@reset_bp.route('/servers/<server_id>/disk-usage')
@require_auth
@require_pin
def disk_page(server_id):
    from ..services.disk_usage_payload import DISPLAY_COMMANDS
    server, _ = target(server_id)
    session.setdefault('csrf_token', secrets.token_urlsafe(32))
    return render_template('disk_usage.html', server=server, commands=DISPLAY_COMMANDS)


@reset_bp.route('/api/servers/<server_id>/disk-usage', methods=['POST'])
@require_auth
@require_pin
@csrf_protect
def disk_run(server_id):
    from ..services.disk_usage_payload import DISK_SOURCE
    _, creds = target(server_id)
    try:
        # Only this fixed read-only payload is sent; request data cannot change commands.
        result = remote(creds, [], source=DISK_SOURCE)
        if 'results' not in result:
            return jsonify(error=translate('Не удалось получить данные о диске.')), 502
        for row in result['results']:
            row['title'] = translate(row['title'])
            if row.get('note'):
                row['note'] = translate(row['note'])
        return jsonify(result)
    except Exception as exc:
        return jsonify(error=describe_failure(exc, creds) or translate('Не удалось выполнить проверку. Проверьте SSH, known_hosts и root/sudo -n.') + failure_code(exc)), 502
