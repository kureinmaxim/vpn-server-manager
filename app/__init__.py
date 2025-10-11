import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request
from flask_babel import Babel
from .config import config_by_name
from .exceptions import AppException
from .services import registry
from .services.ssh_service import SSHService
from .services.crypto_service import CryptoService
from .services.api_service import APIService

def get_translations_path() -> str:
    """Возвращает путь к каталогу переводов с учётом упакованного приложения (PyInstaller)."""
    try:
        is_frozen = getattr(sys, 'frozen', False)
        if is_frozen:
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            candidates = [os.path.join(base_path, 'translations')]
        else:
            base_dir = os.path.dirname(__file__)
            candidates = [
                os.path.join(base_dir, '..', 'translations'),
                'translations',
            ]
        for candidate in candidates:
            if os.path.isdir(candidate):
                return candidate
    except Exception:
        pass
    # Фолбэк — относительный путь; Flask-Babel поддерживает одиночный путь
    return 'translations'

def get_locale():
    """Определяет язык для текущего запроса."""
    # Сначала проверяем параметр в URL
    if request.args.get('lang'):
        return request.args.get('lang')
    
    # Затем проверяем сохраненный язык в сессии
    from flask import session
    if session.get('language'):
        return session.get('language')
    
    # Если язык не установлен в сессии, устанавливаем по умолчанию только один раз
    if 'language_initialized' not in session:
        # Автоопределение языка браузера
        detected_lang = request.accept_languages.best_match(['ru', 'en', 'zh'])
        if detected_lang:
            session['language'] = detected_lang
        else:
            session['language'] = 'ru'  # По умолчанию русский
        session['language_initialized'] = True
        return session['language']
    
    # Если язык уже инициализирован, возвращаем русский по умолчанию
    return 'ru'

def setup_logging(app):
    """Настройка логирования"""
    if not app.debug and not app.testing:
        # Создаем директорию для логов если её нет
        log_dir = os.path.dirname(app.config['LOG_FILE'])
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = RotatingFileHandler(
            app.config['LOG_FILE'],
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        app.logger.info('Application startup')

def register_error_handlers(app):
    """Регистрация обработчиков ошибок"""
    @app.errorhandler(AppException)
    def handle_app_exception(error):
        response = {
            'error': error.__class__.__name__,
            'message': str(error)
        }
        if request.is_json:
            return response, error.status_code
        else:
            from flask import flash, redirect, url_for
            flash(str(error), 'error')
            return redirect(url_for('main.index'))
    
    @app.errorhandler(404)
    def handle_not_found(error):
        if request.is_json:
            return {'error': 'Not found'}, 404
        else:
            from flask import render_template
            return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        app.logger.error(f'Internal error: {str(error)}')
        if request.is_json:
            return {'error': 'Internal server error'}, 500
        else:
            from flask import render_template
            return render_template('500.html'), 500

def load_app_info(app):
    """Загрузка информации о приложении из config.json"""
    try:
        import json
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                app.config['app_info'] = config.get('app_info', {})
        else:
            # Заглушка если config.json не найден
            app.config['app_info'] = {
                "version": "4.0.0",
                "last_updated": "2025-01-15",
                "developer": "Куреин М.Н."
            }
    except Exception as e:
        app.logger.warning(f"Could not load app_info: {e}")
        app.config['app_info'] = {
            "version": "4.0.0",
            "last_updated": "2025-01-15",
            "developer": "Куреин М.Н."
        }

def register_services():
    """Регистрация сервисов в реестре"""
    registry.register('ssh', SSHService())
    registry.register('crypto', CryptoService())
    registry.register('api', APIService())

def create_app(config_name='development'):
    """Application Factory"""
    # Определяем путь к корневой директории проекта
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    app = Flask(__name__, 
                template_folder=os.path.join(project_root, 'templates'),
                static_folder=os.path.join(project_root, 'static'))
    
    # Загрузка конфигурации
    app.config.from_object(config_by_name[config_name])
    
    # Настройка переводов
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = get_translations_path()
    
    # Инициализация расширений
    babel = Babel(app, locale_selector=get_locale)
    
    # Настройка логирования
    setup_logging(app)
    
    # Регистрация сервисов
    register_services()
    
    # Регистрация blueprints
    from .routes import main_bp, api_bp, pin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(pin_bp)
    
    # Обработчики ошибок
    register_error_handlers(app)
    
    # Настройка сессий
    app.config['SESSION_COOKIE_SECURE'] = not app.debug
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Настройка загрузки файлов
    app.config['MAX_CONTENT_LENGTH'] = app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
    
    # Создание необходимых директорий
    for directory in ['uploads', 'logs', 'data']:
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    # Загрузка app_info из config.json
    load_app_info(app)
    
    # Контекстный процессор для app_info
    @app.context_processor
    def inject_app_info():
        """Инжектирует информацию о приложении во все шаблоны."""
        return {'app_info': app.config.get('app_info', {})}
    
    # Jinja фильтр для форматирования даты
    @app.template_filter('format_datetime')
    def format_datetime_filter(iso_str):
        """Jinja фильтр для форматирования ISO-строки с датой и временем."""
        if not iso_str:
            return "N/A"
        try:
            import datetime
            dt = datetime.datetime.fromisoformat(iso_str)
            return dt.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            return iso_str
    
    app.logger.info(f'Application created with config: {config_name}')
    return app
