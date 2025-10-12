import functools
import logging
from flask import request, jsonify, session, redirect, url_for
from typing import Callable, Any
from ..exceptions import AuthenticationError, ValidationError

logger = logging.getLogger(__name__)

def is_api_request():
    """Проверяет, является ли запрос API запросом"""
    # AJAX запрос
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    # JSON запрос
    if request.is_json:
        return True
    # API пути
    if request.path.startswith('/api/') or request.path.startswith('/server/'):
        return True
    # Accept заголовок указывает на JSON
    if 'application/json' in request.headers.get('Accept', ''):
        return True
    return False

def require_auth(f: Callable) -> Callable:
    """Декоратор для проверки аутентификации"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Проверяем, есть ли PIN в сессии
        if not session.get('authenticated'):
            if is_api_request():
                return jsonify({'error': 'Authentication required'}), 401
            else:
                return redirect(url_for('main.index_locked'))
        return f(*args, **kwargs)
    return decorated_function

def require_pin(f: Callable) -> Callable:
    """Декоратор для проверки PIN кода"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('pin_verified'):
            if is_api_request():
                return jsonify({'error': 'PIN verification required'}), 401
            else:
                return redirect(url_for('main.index_locked'))
        return f(*args, **kwargs)
    return decorated_function

def validate_json(f: Callable) -> Callable:
    """Декоратор для валидации JSON данных"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if request.is_json:
            try:
                data = request.get_json()
                if data is None:
                    return jsonify({'error': 'Invalid JSON data'}), 400
            except Exception as e:
                logger.error(f"JSON validation error: {str(e)}")
                return jsonify({'error': 'Invalid JSON format'}), 400
        return f(*args, **kwargs)
    return decorated_function

def handle_errors(f: Callable) -> Callable:
    """Декоратор для обработки ошибок"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            logger.error(f"Validation error in {f.__name__}: {str(e)}")
            if request.is_json:
                return jsonify({'error': str(e)}), 400
            else:
                from flask import flash
                flash(str(e), 'error')
                return redirect(request.url)
        except AuthenticationError as e:
            logger.error(f"Authentication error in {f.__name__}: {str(e)}")
            if request.is_json:
                return jsonify({'error': str(e)}), 401
            else:
                return redirect(url_for('main.index_locked'))
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}")
            if request.is_json:
                return jsonify({'error': 'Internal server error'}), 500
            else:
                from flask import flash
                flash('An unexpected error occurred', 'error')
                return redirect(request.url)
    return decorated_function

def log_request(f: Callable) -> Callable:
    """Декоратор для логирования запросов"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        logger.info(f"Request: {request.method} {request.url} from {request.remote_addr}")
        response = f(*args, **kwargs)
        logger.info(f"Response: {response[1] if isinstance(response, tuple) else '200'}")
        return response
    return decorated_function

def rate_limit(max_requests: int = 100, window: int = 3600):
    """Декоратор для ограничения частоты запросов"""
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Простая реализация rate limiting
            # В production лучше использовать Redis или подобное решение
            client_ip = request.remote_addr
            current_time = time.time()
            
            # Здесь должна быть логика проверки лимитов
            # Для простоты пропускаем все запросы
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def cache_response(timeout: int = 300):
    """Декоратор для кеширования ответов"""
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Простая реализация кеширования
            # В production лучше использовать Redis или Flask-Caching
            cache_key = f"{f.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Здесь должна быть логика проверки кеша
            # Для простоты всегда выполняем функцию
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f: Callable) -> Callable:
    """Декоратор для проверки прав администратора"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Проверяем, является ли пользователь администратором
        if not session.get('is_admin'):
            if request.is_json:
                return jsonify({'error': 'Admin access required'}), 403
            else:
                from flask import flash
                flash('Admin access required', 'error')
                return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def csrf_protect(f: Callable) -> Callable:
    """Декоратор для защиты от CSRF атак"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            # Проверяем CSRF токен
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            if not token or token != session.get('csrf_token'):
                if request.is_json:
                    return jsonify({'error': 'CSRF token mismatch'}), 403
                else:
                    from flask import flash
                    flash('Security token mismatch', 'error')
                    return redirect(request.url)
        return f(*args, **kwargs)
    return decorated_function

import time
