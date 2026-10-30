"""Authenticated diagnostic settings and explicit read-only runs."""
import hmac
import secrets

from flask import Blueprint, abort, current_app, jsonify, render_template, request, session
from flask_babel import gettext as _

from ..services import registry
from ..services.dns_mail import settings, remote_probe, remember
from ..services.ssh_auth import has_ssh_auth
from ..services.ssh_connection import resolve_server_ssh_credentials
from ..utils.decorators import require_auth, require_pin
from .api import load_check_limiter
from .net_tools import _slots

dns_mail_bp = Blueprint('dns_mail', __name__, url_prefix='/diagnostics')


@dns_mail_bp.after_request
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


@dns_mail_bp.route('/<server_id>', methods=['GET', 'POST'])
@require_auth
@require_pin
def detail(server_id):
    manager = registry.get('data_manager')
    if not manager:
        abort(503)
    if request.method == 'GET':
        servers = manager.load_servers(current_app.config)
        server = next((s for s in servers if str(s.get('id')) == server_id), None)
        if not server:
            abort(404)
        session.setdefault('diagnostics_token', secrets.token_urlsafe(32))
        try:
            config = settings(server.get('dns_mail_diagnostics', {}))
        except ValueError:
            config = settings({})
        if request.args.get('role') in ('adguard', 'chatmail'):
            config['role'] = request.args['role']
        response = current_app.make_response(render_template('dns_mail.html', server=server,
                    config=config, token=session['diagnostics_token']))
    else:
        token = session.get('diagnostics_token', '')
        if not token or not hmac.compare_digest(token.encode(), request.headers.get('X-Diagnostics-Token', '').encode()):
            return jsonify(error=_('Обновите страницу и повторите проверку.')), 403
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or data.get('action') not in ('save', 'run'):
            abort(400)
        try:
            config = settings(data.get('config'))
        except (ValueError, TypeError):
            return jsonify(error=_('Некорректные параметры запроса.')), 400
        if data['action'] == 'save':
            servers = manager.load_servers(current_app.config)
            server = next((s for s in servers if str(s.get('id')) == server_id), None)
            if not server:
                abort(404)
            path = manager.get_active_data_path(current_app.config)
            if not path:
                abort(409)
            server['dns_mail_diagnostics'] = config
            manager.save_servers(servers, path)
            response = jsonify(saved=True)
        else:
            if not load_check_limiter.is_allowed('diagnostics:' + server_id) or not _slots.acquire(blocking=False):
                return jsonify(error=_('Дождитесь завершения предыдущих проверок.')), 429
            try:
                server, creds = resolve_server_ssh_credentials(server_id, manager, current_app.config)
                if not server or not has_ssh_auth(creds):
                    return jsonify(error=_('Укажите IP и пароль или SSH-ключ в карточке сервера.')), 400
                client = registry.get('ssh').get_connection_pooled(
                    hostname=creds['ip'], username=creds['user'], port=creds['port'],
                    password=creds.get('password'), key=creds.get('key'),
                    key_passphrase=creds.get('key_passphrase'), connection_timeout=5)
                results = remote_probe(client, config)
                remember(client, config, results)
                response = jsonify(results=results)
            except Exception:
                # Neither exception text nor remote stderr is logged or returned.
                return jsonify(error=_('SSH-проверка недоступна. Проверьте подключение, права и Python 3 на VPS.')), 502
            finally:
                _slots.release()
    response.headers['Cache-Control'] = 'no-store'
    return response
