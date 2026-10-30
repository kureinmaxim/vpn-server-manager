"""Чеки хранятся отдельно от публичных иконок; доступ только через карточку."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, abort, current_app, jsonify, request, send_from_directory
from flask_babel import gettext as _
from werkzeug.exceptions import HTTPException

from ..services import registry
from ..services.profile_transaction import profile_lock
from ..services.vault_io import VaultError
from ..utils.decorators import require_auth, require_pin, csrf_protect

receipts_bp = Blueprint('receipts', __name__)


@receipts_bp.errorhandler(HTTPException)
@receipts_bp.errorhandler(VaultError)
@receipts_bp.errorhandler(OSError)
def receipt_error(error):
    return jsonify(error=_('Не удалось обработать чек.')), getattr(error, 'code', 409) or 409


@receipts_bp.after_request
def private_response(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


def inventory(server_id):
    manager = registry.get('data_manager')
    if manager is None:
        abort(503)
    servers = manager.load_servers(current_app.config)
    server = next((s for s in servers if str(s['id']) == server_id), None)
    if server is None:
        abort(404)
    path = manager.get_active_data_path(current_app.config)
    if not path:
        abort(409)
    return manager, servers, server, path


def receipt_dir():
    return Path(current_app.config['UPLOAD_FOLDER']) / 'receipts'


@receipts_bp.post('/server/<server_id>/receipts/add')
@require_auth
@require_pin
@csrf_protect
def add(server_id):
    upload = request.files.get('receipt_file')
    description = request.form.get('description', '').strip()
    original = Path((upload.filename or '').replace('\\', '/')).name if upload else ''
    if len(original) > 255 or any(ord(char) < 32 for char in original):
        abort(400)
    extension = Path(original).suffix.lower()
    if not upload or not description or len(description) > 500 or extension not in {'.pdf', '.png', '.jpg', '.jpeg', '.webp'}:
        abort(400)
    with profile_lock(current_app.config['APP_DATA_DIR']):
        manager, servers, server, path = inventory(server_id)
        folder = receipt_dir()
        folder.mkdir(parents=True, exist_ok=True)
        filename = uuid4().hex + extension
        destination = folder / filename
        stamp = datetime.now(timezone.utc).isoformat()
        receipt = dict(filename=filename, original_name=original, description=description,
                       upload_date=stamp)
        try:
            with destination.open('xb') as stream:
                upload.save(stream)
            if destination.stat().st_size == 0:
                abort(400)
            server.setdefault('payment_info', {}).setdefault('receipts', []).append(receipt)
            manager.save_servers(servers, path)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    return jsonify(**receipt, formatted_date=stamp)


@receipts_bp.get('/server/<server_id>/receipts/file/<filename>')
@require_auth
@require_pin
def download(server_id, filename):
    _, _, server, _ = inventory(server_id)
    receipt = next((r for r in server.get('payment_info', {}).get('receipts', [])
                    if r.get('filename') == filename), None)
    if receipt is None or Path(filename).name != filename:
        abort(404)
    response = send_from_directory(receipt_dir(), filename, as_attachment=True,
                                   download_name=receipt.get('original_name') or filename)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@receipts_bp.post('/server/<server_id>/receipts/delete/<filename>')
@require_auth
@require_pin
@csrf_protect
def delete(server_id, filename):
    with profile_lock(current_app.config['APP_DATA_DIR']):
        manager, servers, server, path = inventory(server_id)
        receipts = server.get('payment_info', {}).get('receipts', [])
        receipt = next((r for r in receipts if r.get('filename') == filename), None)
        if receipt is None or Path(filename).name != filename:
            abort(404)
        receipts.remove(receipt)
        manager.save_servers(servers, path)
        # Сначала сохраняем метаданные: ошибка записи не должна уничтожить файл.
        (receipt_dir() / filename).unlink(missing_ok=True)
    return jsonify(success=True)
