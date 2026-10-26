"""Общая защита изменяющих HTTP-запросов, включая локальный WebView."""
import hmac
import secrets
from flask import jsonify, request, session
from flask_babel import gettext as _
from ..utils.rate_limiter import RateLimiter


def install(app):
    if not app.config.get('TRUSTED_HOSTS'):
        app.config['TRUSTED_HOSTS'] = ['localhost', '127.0.0.1', '[::1]']
    # Состояние на сервере: новая cookie не сбрасывает лимит PIN.
    limiter = RateLimiter(max_requests=10, time_window=60)
    app.extensions['pin_limiter'] = limiter

    @app.before_request
    def guard():
        session.setdefault('csrf_token', secrets.token_urlsafe(32))
        if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return None
        view = app.view_functions.get(request.endpoint)
        # Existing auth decorators reject before the route can mutate anything.
        if ((getattr(view, 'requires_auth', False) and not session.get('authenticated')) or
                (getattr(view, 'requires_pin', False) and not session.get('pin_verified'))):
            return None
        origin = request.headers.get('Origin')
        if origin and origin != request.host_url.rstrip('/'):
            return jsonify(error=_('Запрос отклонён: другой источник.')), 403
        token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token', '')
        if not isinstance(token, str) or not hmac.compare_digest(token.encode(), session['csrf_token'].encode()):
            return jsonify(error=_('Защитный токен устарел. Обновите страницу.')), 403
        if request.endpoint in ('pin.login_ajax', 'pin.change_ajax', 'pin.first_time_setup', 'main.verify_pin'):
            if not limiter.is_allowed('pin'):
                return jsonify(error=_('Слишком частые проверки. Повторите через минуту.')), 429
        return None
