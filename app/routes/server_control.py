"""Session-bound plans for targeted SSH service management."""
import json
import secrets
import time
import re

from flask import Blueprint, jsonify, render_template, request, session
from flask_babel import gettext as _

from .reset import target, identity, remote, _guard, _locks
from ..services.server_control_payload import SCRIPT_SOURCE
from ..services.server_control_remote import CATALOG, ACTIONS
from ..services.protocol_inspection import PROTOCOL_FILES
from ..services.protocol_mutations import validate_change, MUTATION_PROTOCOLS
from ..utils.decorators import require_auth, require_pin, csrf_protect
import threading

control_bp = Blueprint("server_control", __name__)
_pending = {}
TTL = 300


def mutation_error(code):
    messages = {
        'bot_running': _("Сначала остановите TelegramOnly: одновременное изменение настроек ботом не поддерживается."),
        'config_mismatch': _("Настройки менеджера отличаются от файла службы. Изменения заблокированы."),
        'unsupported_runtime': _("Изменение доступно для одной работающей службы systemd с выделенным конфигом sing-box, Xray или Hysteria2."),
        'unsupported_config': _("Этот формат конфигурации пока доступен только для чтения."),
        'ambiguous_config': _("Найдено несколько файлов настроек. Изменения заблокированы."),
        'shared_password': _("Общий пароль Hysteria2: доступна только смена порта. Переход на отдельных клиентов требует отдельной настройки."),
        'protected_client': _("Клиент default защищён: TelegramOnly может восстановить его из основного UUID или пароля."),
        'managed_by_panel': _("Обнаружена 3x-ui. Изменяйте VLESS через панель владельца конфигурации."),
        'client_exists': _("Клиент с таким именем уже существует."),
        'client_missing': _("Клиент больше не существует. Прочитайте настройки заново."),
        'last_client': _("Нельзя удалить последнего клиента."),
        'validation_failed': _("Проверка конфигурации службой не прошла. Рабочие файлы не изменены."),
        'rolled_back': _("Изменение не применилось. Предыдущие файлы восстановлены, служба работает."),
        'recovery_required': _("Требуется восстановление по SSH. Резервная копия сохранена; новые изменения заблокированы."),
        'unsafe_path': _("Права или расположение файлов не позволяют безопасно изменить конфигурацию."),
    }
    return messages.get(code, _("Цель изменилась. Обновите состояние и создайте новый план."))


def invoke(creds, body):
    return remote(creds, [json.dumps(body, separators=(",", ":"))], source=SCRIPT_SOURCE)


def remote_error():
    return jsonify(error=_("Не удалось выполнить операцию. Проверьте SSH, known_hosts и root/sudo -n. После потери ответа обновите состояние перед повтором.")), 502


def localize_inventory(result):
    for component in result.get("components", []):
        component["title"] = _(component["title"])
    return result


@control_bp.after_request
def private_response(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@control_bp.route("/servers/<server_id>/control")
@require_auth
@require_pin
def page(server_id):
    server, _creds = target(server_id)
    session.setdefault("csrf_token", secrets.token_urlsafe(32))
    return render_template("server_control.html", server=server, mutation_protocols=MUTATION_PROTOCOLS)


@control_bp.route("/api/servers/<server_id>/control/discover", methods=["POST"])
@require_auth
@require_pin
@csrf_protect
def discover(server_id):
    server, creds = target(server_id)
    try:
        result = invoke(creds, {"operation": "discover"})
        if "components" not in result:
            return remote_error()
        return jsonify(localize_inventory(result))
    except Exception:
        return remote_error()


@control_bp.route("/api/servers/<server_id>/control/protocols", methods=["POST"])
@require_auth
@require_pin
@csrf_protect
def protocols(server_id):
    server, creds = target(server_id)
    try:
        result = invoke(creds, {"operation": "protocols"})
        if not isinstance(result.get("protocols"), list):
            return remote_error()
        return jsonify(result)
    except Exception:
        return remote_error()


@control_bp.route("/api/servers/<server_id>/control/clients/<operation>", methods=["POST"])
@require_auth
@require_pin
@csrf_protect
def clients(server_id, operation):
    body = request.get_json(silent=True)
    if operation not in ('list', 'export') or not isinstance(body, dict):
        return jsonify(error=_("Неверный запрос клиента")), 400
    if not isinstance(body.get('component'), str) or body['component'] not in PROTOCOL_FILES or any(
        not isinstance(body.get(key), str) or not re.fullmatch('[0-9a-f]{64}', body[key])
        for key in ('source_id', 'revision')
    ):
        return jsonify(error=_("Неверный запрос клиента")), 400
    command = {key: body[key] for key in ('component', 'source_id', 'revision')}
    command['operation'] = 'clients' if operation == 'list' else 'export_client'
    if operation == 'export':
        if type(body.get('index')) is not int or not 0 <= body['index'] < 10000:
            return jsonify(error=_("Неверный запрос клиента")), 400
        command['index'] = body['index']
    server, creds = target(server_id)
    try:
        result = invoke(creds, command)
        expected = 'clients' if operation == 'list' else 'profile'
        if expected not in result:
            return jsonify(error=_("Конфигурация изменилась или профиль не поддерживается. Прочитайте настройки заново.")), 409
        return jsonify(result)
    except Exception:
        return remote_error()


@control_bp.route("/api/servers/<server_id>/control/plan", methods=["POST"])
@require_auth
@require_pin
@csrf_protect
def create_plan(server_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(error=_("Выберите службу и действие")), 400
    if body.get('action') == 'configure':
        try:
            if body.get('component') not in MUTATION_PROTOCOLS or any(not isinstance(body.get(k), str) or not re.fullmatch('[0-9a-f]{64}', body[k]) for k in ('source_id', 'revision')):
                raise ValueError()
            command = {k: body[k] for k in ('component', 'action', 'source_id', 'revision')}
            command['change'] = validate_change(body.get('change'))
        except ValueError:
            return jsonify(error=_("Неверные параметры изменения")), 400
    else:
        if not all(isinstance(body.get(k), str) for k in ("component", "action", "instance", "runtime")):
            return jsonify(error=_("Выберите службу и действие")), 400
        if body["component"] not in CATALOG or body["action"] not in ACTIONS or body["runtime"] not in ("docker", "systemd") or len(body["instance"]) > 256:
            return jsonify(error=_("Выберите службу и действие")), 400
        command = {k: body[k] for k in ("component", "action", "instance", "runtime")}
    server, creds = target(server_id)
    try:
        plan = invoke(creds, dict(command, operation="plan"))
        if not isinstance(plan.get("plan_hash"), str) or not isinstance(plan.get("hostname"), str):
            return jsonify(error=mutation_error(plan.get('error'))), 409
    except Exception:
        return remote_error()
    owner = session.setdefault("control_session", secrets.token_urlsafe(32))
    ticket = secrets.token_urlsafe(32)
    with _guard:
        now = time.monotonic()
        for key, value in list(_pending.items()):
            if now - value["time"] > TTL or (value["owner"] == owner and value["server"] == server_id):
                _pending.pop(key, None)
        _pending[ticket] = dict(owner=owner, server=server_id, identity=identity(creds), time=now, plan=plan, command=command)
    return jsonify(ticket=ticket, plan=plan, expires_in=TTL)


@control_bp.route("/api/servers/<server_id>/control/apply", methods=["POST"])
@require_auth
@require_pin
@csrf_protect
def apply_plan(server_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not isinstance(body.get("ticket"), str):
        return jsonify(error=_("Сначала создайте план")), 400
    server, creds = target(server_id)
    with _guard:
        item = _pending.get(body["ticket"])
        if (not item or item["owner"] != session.get("control_session") or item["server"] != server_id
                or item["identity"] != identity(creds) or time.monotonic() - item["time"] > TTL):
            return jsonify(error=_("План устарел или относится к другому серверу/сеансу")), 409
        if body.get("confirmation") != item["plan"]["hostname"]:
            return jsonify(error=_("Введите точное имя VPS")), 400
        lock = _locks.setdefault(identity(creds)[:2], threading.Lock())
        if not lock.acquire(blocking=False):
            return jsonify(error=_("Другая операция уже выполняется")), 409
        _pending.pop(body["ticket"])
    try:
        result = invoke(creds, dict(item["command"], operation="apply", plan_hash=item["plan"]["plan_hash"], confirmation=item["plan"]["hostname"]))
        if not result.get("success"):
            result["error"] = mutation_error(result.get('error')) if item['command']['action'] == 'configure' else _("Операция не подтверждена. Обновите состояние: служба могла измениться или команда завершилась с ошибкой.")
        if "inventory" in result:
            localize_inventory(result["inventory"])
        return jsonify(result), (200 if result.get("success") else 409)
    except Exception:
        return remote_error()
    finally:
        lock.release()
