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
from .services.data_manager_service import DataManagerService

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
    from flask import session
    
    # Сначала проверяем параметр в URL
    if request.args.get('lang'):
        lang = request.args.get('lang')
        session['language'] = lang
        session.permanent = True
        return lang
    
    # Затем проверяем сохраненный язык в сессии
    if 'language' in session:
        return session.get('language')
    
    # Если язык не установлен, автоопределяем по браузеру
    detected_lang = request.accept_languages.best_match(['ru', 'en', 'zh'])
    if detected_lang:
        session['language'] = detected_lang
    else:
        session['language'] = 'ru'  # По умолчанию русский
    
    session.permanent = True
    return session['language']

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

def manage_user_config(app):
    """
    Управляет конфигурационным файлом пользователя (config.json) в APP_DATA_DIR.
    При первом запуске копирует config.json из бандла и удаляет active_data_file.
    """
    if not getattr(sys, 'frozen', False):
        return  # В режиме разработки ничего не делаем

    import json
    import shutil
    
    app_data_dir = app.config.get('APP_DATA_DIR')
    user_config_path = os.path.join(app_data_dir, 'config.json')

    if not os.path.exists(user_config_path):
        try:
            # Копируем config.json из бандла (_MEIPASS) в папку данных пользователя
            bundle_config_path = os.path.join(getattr(sys, '_MEIPASS', '.'), 'config.json')
            if os.path.exists(bundle_config_path):
                shutil.copy2(bundle_config_path, user_config_path)
                app.logger.info(f"Copied config.json to {user_config_path}")

                # Удаляем ключ active_data_file, чтобы заставить пользователя выбрать файл
                with open(user_config_path, 'r+') as f:
                    config = json.load(f)
                    if 'active_data_file' in config:
                        del config['active_data_file']
                        f.seek(0)
                        json.dump(config, f, indent=2, ensure_ascii=False)
                        f.truncate()
                        app.logger.info("Removed 'active_data_file' from user config on first run.")
        except Exception as e:
            app.logger.error(f"Failed to manage user config on first run: {e}")


def load_app_info(app):
    """Загрузка информации о приложении и конфигурации из config.json"""
    try:
        import json
        
        # В режиме разработки используем config.json из корня проекта
        # В собранном приложении используем config.json из APP_DATA_DIR
        if getattr(sys, 'frozen', False):
            # Режим PyInstaller: используем папку данных приложения
            base_path = app.config.get('APP_DATA_DIR')
        else:
            # Обычный режим: корень проекта
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        config_path = os.path.join(base_path, 'config.json') if base_path else None

        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                app.config['app_info'] = config.get('app_info', {})
                # Загружаем active_data_file если он есть
                if 'active_data_file' in config:
                    app.config['active_data_file'] = config['active_data_file']
                    app.logger.info(f"Loaded active_data_file: {config['active_data_file']}")
        else:
            # Заглушка если config.json не найден
            app.config['app_info'] = {
                "version": "4.0.9",
                "last_updated": "2025-10-25",
                "developer": "Куреин М.Н."
            }
    except Exception as e:
        app.logger.warning(f"Could not load app_info: {e}")
        app.config['app_info'] = {
            "version": "4.0.9",
            "last_updated": "2025-10-25",
            "developer": "Куреин М.Н."
        }

def register_services(app):
    """Регистрация сервисов в реестре"""
    import logging
    logger = logging.getLogger(__name__)
    
    registry.register('ssh', SSHService())
    registry.register('crypto', CryptoService())
    registry.register('api', APIService())
    
    # DataManagerService требует secret_key и app_data_dir
    secret_key = app.config.get('SECRET_KEY')
    app_data_dir = app.config.get('APP_DATA_DIR')
    
    logger.info(f"Attempting to register DataManagerService...")
    logger.info(f"  SECRET_KEY exists: {secret_key is not None}")
    logger.info(f"  SECRET_KEY length: {len(secret_key) if secret_key else 0}")
    logger.info(f"  APP_DATA_DIR: {app_data_dir}")
    
    # Проверяем, что ключ валидный для Fernet
    if secret_key and app_data_dir:
        try:
            from cryptography.fernet import Fernet
            # Проверяем формат ключа
            logger.info(f"  Validating Fernet key...")
            Fernet(secret_key.encode() if isinstance(secret_key, str) else secret_key)
            logger.info(f"  Fernet key is valid ✓")
            data_manager = DataManagerService(secret_key, app_data_dir)
            registry.register('data_manager', data_manager)
            logger.info(f"✅ DataManagerService registered successfully")
        except Exception as e:
            # Если ключ невалидный, логируем предупреждение но не падаем
            logger.error(f"❌ Cannot initialize DataManagerService: {e}")
            logger.error(f"   SECRET_KEY type: {type(secret_key)}")
            logger.error(f"   SECRET_KEY preview: {secret_key[:20] if secret_key else 'None'}...")
    else:
        logger.error(f"❌ DataManagerService NOT registered: missing SECRET_KEY or APP_DATA_DIR")
        if not secret_key:
            logger.error(f"   SECRET_KEY is missing!")
        if not app_data_dir:
            logger.error(f"   APP_DATA_DIR is missing!")

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

    # Управление пользовательским config.json (только для frozen-режима)
    manage_user_config(app)
    
    # Настройка переводов
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = get_translations_path()
    
    # Инициализация расширений
    babel = Babel(app, locale_selector=get_locale)
    
    # Настройка логирования
    setup_logging(app)
    
    # Регистрация сервисов
    register_services(app)
    
    # Регистрация blueprints
    from .routes import main_bp, api_bp, pin_bp, vendor_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(pin_bp)
    app.register_blueprint(vendor_bp)
    
    # Обработчики ошибок
    register_error_handlers(app)
    
    # Настройка сессий
    # SESSION_COOKIE_SECURE должен быть False для локального HTTP-сервера
    app.config['SESSION_COOKIE_SECURE'] = False
    # Для pywebview на Windows нужно отключить HTTPONLY и SAMESITE
    app.config['SESSION_COOKIE_HTTPONLY'] = False  # pywebview требует доступ к cookies
    app.config['SESSION_COOKIE_SAMESITE'] = None  # Иначе не работает в desktop режиме
    # НЕ используем filesystem - сессии хранятся только в cookie и сбрасываются при закрытии
    # app.config['SESSION_TYPE'] = 'filesystem'  # Закомментировано: сохраняет сессии между запусками!
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 час (если session.permanent = True)
    
    # Уникальное имя cookie для изоляции сессий при параллельном запуске
    app.config['SESSION_COOKIE_NAME'] = 'vpn_manager_session_clean'
    
    # Настройка загрузки файлов
    app.config['MAX_CONTENT_LENGTH'] = app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
    
    # Создаём необходимые директории - используем пути из конфига
    upload_dir = app.config.get('UPLOAD_FOLDER')
    data_dir = app.config.get('DATA_DIR')
    
    # Создаём директории, если указаны
    if upload_dir:
        os.makedirs(upload_dir, exist_ok=True)
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)
    
    # Создаём директорию для логов (если не frozen)
    if not getattr(sys, 'frozen', False):
        os.makedirs('logs', exist_ok=True)
    
    # Загрузка app_info из config.json
    load_app_info(app)
    
    # Контекстный процессор для app_info
    @app.context_processor
    def inject_app_info():
        """Инжектирует информацию о приложении во все шаблоны."""
        from flask import request
        
        # Определяем адрес и порт сервера
        server_host = request.host.split(':')[0] if ':' in request.host else request.host
        server_port = request.host.split(':')[1] if ':' in request.host else '5000'
        server_url = f"http://{request.host}"
        
        return {
            'app_info': app.config.get('app_info', {}),
            'server_info': {
                'host': server_host,
                'port': server_port,
                'url': server_url
            }
        }
    
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
