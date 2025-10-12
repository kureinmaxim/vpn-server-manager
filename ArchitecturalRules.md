# Архитектурные правила для Flask-приложения v4.0.3

## Контекст проекта

**VPN Server Manager** - Flask-приложение с desktop GUI (pywebview), поддержкой интернационализации, SSH/SFTP функциональностью и криптографией.

**v4.0.3**: 
- ✅ Централизованное управление версией из `config.json`
- ✅ Multi-App Support (параллельный запуск)
- ✅ Модульная архитектура (Application Factory, Service Layer)
- ✅ DataManagerService для управления данными

## Структура проекта (v4.0.3)

```
VPNserverManage-Clean/
├── run.py                        # Точка входа (web/desktop режимы)
├── config.json                   # 🎯 Конфигурация (version: 4.0.3)
├── .env                          # Секреты (SECRET_KEY)
├── .env.example
├── .gitignore
├── requirements.txt
├── setup.py                      # Автоматически читает версию из config.json
├── build_macos.py                # Сборка с версией из config.json
├── Makefile                      # Команды разработки
├── babel.cfg                     # Babel конфигурация
│
├── app/                          # Основное приложение
│   ├── __init__.py              # Application Factory + load_app_info
│   ├── config.py                # Конфигурация (APP_DATA_DIR, APP_VERSION)
│   ├── exceptions.py            # Кастомные исключения
│   ├── models/                  # Модели данных
│   │   ├── __init__.py
│   │   └── server.py           # Модель VPN сервера
│   ├── services/                # Бизнес-логика (Service Layer)
│   │   ├── __init__.py         # ServiceRegistry (Dependency Injection)
│   │   ├── ssh_service.py      # SSH/SFTP операции
│   │   ├── crypto_service.py   # Шифрование/дешифрование
│   │   ├── api_service.py      # HTTP API запросы
│   │   └── data_manager_service.py  # 🆕 Управление данными (v4.0.1+)
│   ├── routes/                  # Маршруты (Blueprint Architecture)
│   │   ├── __init__.py
│   │   ├── main.py             # Основные роуты + /shutdown (v4.0.2)
│   │   └── api.py              # API endpoints + PIN auth
│   └── utils/                   # Утилиты
│       ├── __init__.py
│       ├── validators.py
│       └── decorators.py       # @require_auth, @require_pin
│
├── desktop/                     # Desktop GUI слой
│   ├── __init__.py
│   └── window.py               # 🆕 WSGI + динамические порты (v4.0.2)
│
├── templates/                   # Jinja2 шаблоны (вне app/)
│   ├── layout.html
│   ├── index.html
│   ├── index_locked.html       # PIN вход
│   ├── settings.html
│   └── ...
│
├── static/                      # Статические файлы (вне app/)
│   ├── css/
│   ├── js/
│   ├── images/
│   └── fonts/
│
├── translations/                # Flask-Babel переводы (вне app/)
│   ├── en/LC_MESSAGES/
│   ├── ru/LC_MESSAGES/
│   └── zh/LC_MESSAGES/
│
├── data/                        # Данные приложения
│   ├── servers.json.enc        # Зашифрованные серверы
│   └── merged_*.enc            # Импортированные данные
│
├── uploads/                     # Загруженные иконки серверов
├── logs/                        # Логи приложения
│   └── app.log
│
├── tests/                       # Тесты
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_services/
│   └── test_routes/
│
├── docs/                        # Документация
│   ├── project_info/
│   │   ├── PROJECT_STRUCTURE.md
│   │   ├── BUILD.md
│   │   ├── BACKUP_TOOLS.md
│   │   └── SECRET_KEY.md
│   ├── release_guide.md
│   └── github_push_guide.md
│
└── backup_tools/                # Инструменты резервного копирования
    └── ...
```
## 1. Application Factory Pattern

**ОБЯЗАТЕЛЬНО**: Используйте паттерн Application Factory для создания Flask-приложения.

**v4.0.3**: Application Factory автоматически загружает версию из `config.json`.

```python
# app/__init__.py
from flask import Flask
from flask_babel import Babel
from .config import config_by_name

def load_app_info(app):
    """Загрузка информации о приложении из config.json"""
    try:
        import json
        app_data_dir = app.config.get('APP_DATA_DIR')
        config_path = os.path.join(app_data_dir, 'config.json') if app_data_dir \
                      else os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                app.config['app_info'] = config.get('app_info', {})
                # Загружаем active_data_file если он есть
                if 'active_data_file' in config:
                    app.config['active_data_file'] = config['active_data_file']
    except Exception as e:
        app.logger.warning(f"Could not load app_info: {e}")
        # Fallback версия
        app.config['app_info'] = {
            "version": "4.0.3",
            "last_updated": "2025-10-12",
            "developer": "Куреин М.Н."
        }

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    
    # Инициализация расширений
    babel = Babel(app, locale_selector=get_locale)
    
    # Регистрация сервисов
    register_services(app)
    
    # Регистрация blueprints
    from .routes import main_bp, api_bp, pin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(pin_bp, url_prefix='/pin')
    
    # Обработчики ошибок
    register_error_handlers(app)
    
    # Настройка сессий (v4.0.2: уникальные cookie)
    app.config['SESSION_COOKIE_NAME'] = 'vpn_manager_session_clean'
    
    # Загрузка app_info из config.json
    load_app_info(app)
    
    # Контекстный процессор для app_info
    @app.context_processor
    def inject_app_info():
        return {'app_info': app.config.get('app_info', {})}
    
    return app
```
## 2. Конфигурация через переменные окружения + config.json

**ПРАВИЛО**: Чувствительные данные в `.env`, настройки приложения в `config.json`.

**v4.0.3**: Версия хранится **ТОЛЬКО** в `config.json` и загружается автоматически!

```python
# app/config.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_app_data_dir():
    """
    Возвращает директорию для хранения данных приложения.
    Production: ~/Library/Application Support/VPNServerManager-Clean/ (macOS)
    Development: текущая директория проекта
    """
    is_frozen = getattr(sys, 'frozen', False)
    app_name = "VPNServerManager-Clean"
    
    if is_frozen:  # Упакованное приложение
        if sys.platform == 'darwin':  # macOS
            app_data_dir = os.path.join(
                os.path.expanduser("~"), 
                "Library", "Application Support", 
                app_name
            )
        elif sys.platform == 'win32':  # Windows
            app_data_dir = os.path.join(
                os.getenv('APPDATA', os.path.expanduser("~")),
                app_name
            )
        else:  # Linux
            app_data_dir = os.path.join(
                os.path.expanduser("~"),
                ".local", "share",
                app_name
            )
    else:  # Режим разработки
        app_data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    os.makedirs(app_data_dir, exist_ok=True)
    return app_data_dir

class Config:
    """Базовая конфигурация"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    BABEL_DEFAULT_LOCALE = os.getenv('BABEL_DEFAULT_LOCALE', 'ru')
    BABEL_TRANSLATION_DIRECTORIES = 'translations'
    BABEL_SUPPORTED_LOCALES = ['ru', 'en', 'zh']
    
    # v4.0.3: Версия из config.json (fallback)
    APP_VERSION = os.getenv('APP_VERSION', '4.0.3')
    APP_NAME = 'VPNServerManager-Clean'
    APP_DATA_DIR = get_app_data_dir()
    
    # Настройки данных
    DATA_DIR = os.getenv('DATA_DIR', 'data')
    SERVERS_FILE = os.getenv('SERVERS_FILE', 'servers.json.enc')
    
    # API URLs
    IP_CHECK_API = os.getenv('IP_CHECK_API', 'https://ipinfo.io/{ip}/json')
    GENERAL_IP_TEST = os.getenv('GENERAL_IP_TEST', 'https://browserleaks.com/ip')
    
    # Настройки загрузки файлов
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '16777216'))
    ALLOWED_EXTENSIONS = {'enc', 'env', 'txt', 'zip', 'json'}
    
    # Настройки логирования
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    
class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = 'WARNING'

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    DATA_DIR = 'test_data'
    
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}
```

**config.json** (источник истины для версии):
```json
{
  "SECRET_KEY_FILE": ".env",
  "app_info": {
    "version": "4.0.3",
    "release_date": "12.10.2025",
    "developer": "Куреин М.Н.",
    "last_updated": "2025-10-12"
  },
  "service_urls": { ... },
  "active_data_file": "...",
  "secret_pin": { ... }
}
```
## 3. Слой сервисов (Service Layer)

**ПРИНЦИП**: Вся бизнес-логика изолирована в отдельном слое сервисов.

**v4.0.3**: Добавлен `DataManagerService` для управления данными, экспорта/импорта.

```python
# app/services/__init__.py
class ServiceRegistry:
    """Реестр сервисов (Dependency Injection)"""
    _services = {}
    
    @classmethod
    def register(cls, name: str, service):
        cls._services[name] = service
    
    @classmethod
    def get(cls, name: str):
        return cls._services.get(name)

registry = ServiceRegistry()

# app/__init__.py (регистрация сервисов)
def register_services(app):
    """Регистрация сервисов в реестре"""
    from .services.ssh_service import SSHService
    from .services.crypto_service import CryptoService
    from .services.api_service import APIService
    from .services.data_manager_service import DataManagerService
    
    registry.register('ssh', SSHService())
    registry.register('crypto', CryptoService())
    registry.register('api', APIService())
    
    # DataManagerService требует secret_key и app_data_dir
    secret_key = app.config.get('SECRET_KEY')
    app_data_dir = app.config.get('APP_DATA_DIR')
    if secret_key and app_data_dir:
        data_manager = DataManagerService(secret_key, app_data_dir)
        registry.register('data_manager', data_manager)
```

### SSHService
```python
# app/services/ssh_service.py
import paramiko
from typing import Optional
from ..exceptions import SSHConnectionError

class SSHService:
    """Сервис для работы с SSH/SFTP"""
    
    def __init__(self):
        self.client: Optional[paramiko.SSHClient] = None
    
    def connect(self, hostname: str, username: str, 
                password: Optional[str] = None,
                key_filename: Optional[str] = None) -> None:
        """Установка SSH соединения"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                hostname=hostname,
                username=username,
                password=password,
                key_filename=key_filename
            )
        except Exception as e:
            raise SSHConnectionError(f"Failed to connect: {str(e)}")
    
    def execute_command(self, command: str) -> tuple:
        """Выполнение команды на сервере"""
        if not self.client:
            raise SSHConnectionError("Not connected")
        stdin, stdout, stderr = self.client.exec_command(command)
        return stdout.read().decode(), stderr.read().decode()
    
    def disconnect(self) -> None:
        """Закрытие соединения"""
        if self.client:
            self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
```

### CryptoService
```python
# app/services/crypto_service.py
from cryptography.fernet import Fernet
import base64

class CryptoService:
    """Сервис для криптографических операций"""
    
    @staticmethod
    def generate_key() -> bytes:
        """Генерация ключа шифрования"""
        return Fernet.generate_key()
    
    @staticmethod
    def encrypt(data: str, key: bytes) -> str:
        """Шифрование данных"""
        f = Fernet(key)
        encrypted = f.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    
    @staticmethod
    def decrypt(encrypted_data: str, key: bytes) -> str:
        """Дешифрование данных"""
        f = Fernet(key)
        decrypted = f.decrypt(base64.b64decode(encrypted_data))
        return decrypted.decode()
```

### DataManagerService (v4.0.1+)
```python
# app/services/data_manager_service.py
from cryptography.fernet import Fernet
import json
import os

class DataManagerService:
    """Сервис для управления данными (экспорт/импорт/бэкап)"""
    
    def __init__(self, secret_key: str, app_data_dir: str):
        self.secret_key = secret_key
        self.app_data_dir = app_data_dir
        self.fernet = Fernet(secret_key.encode() if isinstance(secret_key, str) else secret_key)
    
    def load_servers(self, config):
        """Загрузка серверов из активного файла"""
        active_file = config.get('active_data_file')
        if not active_file or not os.path.exists(active_file):
            return []
        
        try:
            with open(active_file, 'rb') as f:
                encrypted_data = f.read()
            decrypted = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted.decode('utf-8'))
        except Exception as e:
            logger.error(f"Error loading servers: {e}")
            return []
    
    def save_servers(self, servers, filepath):
        """Сохранение серверов в зашифрованный файл"""
        try:
            json_data = json.dumps(servers, ensure_ascii=False, indent=2)
            encrypted = self.fernet.encrypt(json_data.encode('utf-8'))
            with open(filepath, 'wb') as f:
                f.write(encrypted)
            return True
        except Exception as e:
            logger.error(f"Error saving servers: {e}")
            return False
    
    def export_data(self, export_dir):
        """Экспорт данных"""
        # ... реализация экспорта
    
    def import_data(self, file_path):
        """Импорт данных"""
        # ... реализация импорта
```
4. Blueprints для модульности
ПРАВИЛО: Разделяйте функциональность на blueprints.

python
# app/routes/main.py
from flask import Blueprint, render_template
from flask_babel import _

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html', title=_('Home'))
5. Обработка исключений
ПРИНЦИП: Создавайте кастомные исключения и централизованные обработчики.

python
# app/exceptions.py
class AppException(Exception):
    """Базовое исключение приложения"""
    status_code = 500
    
class SSHConnectionError(AppException):
    status_code = 503
    
class CryptoError(AppException):
    status_code = 500

# app/__init__.py (продолжение)
def register_error_handlers(app):
    @app.errorhandler(AppException)
    def handle_app_exception(error):
        response = {
            'error': error.__class__.__name__,
            'message': str(error)
        }
        return response, error.status_code
6. Интернационализация (i18n)
ПРАВИЛО: Используйте Flask-Babel для всех пользовательских текстов.

python
# app/__init__.py
from flask_babel import Babel

def get_locale():
    """Определение локали пользователя"""
    return request.accept_languages.best_match(['en', 'ru'])

babel = Babel(app, locale_selector=get_locale)

# В шаблонах и коде
from flask_babel import gettext as _
message = _('Welcome to application')
## 7. Desktop GUI с pywebview (v4.0.2 - Multi-App Support)

**АРХИТЕКТУРА**: Разделяйте web и desktop слои.

**v4.0.2+**: WSGI сервер с динамическим портом (порт 0) для параллельного запуска.

```python
# desktop/window.py
import webview
import threading
import time
import signal
from wsgiref.simple_server import make_server
from app import create_app

# Глобальные переменные для управления сервером
SERVER_PORT = None
_WSGI_SERVER = None

class DesktopApp:
    def __init__(self, config_name='production'):
        self.config_name = config_name
        self.app = None
        self.window = None
        self.server_thread = None
    
    def create_flask_app(self):
        """Создание Flask приложения"""
        self.app = create_app(self.config_name)
        return self.app
    
    def start_flask_server(self):
        """Запуск Flask сервера с динамическим портом"""
        global SERVER_PORT, _WSGI_SERVER
        
        if self.app:
            # Порт 0 = ОС автоматически выбирает свободный порт
            _WSGI_SERVER = make_server('127.0.0.1', 0, self.app)
            SERVER_PORT = _WSGI_SERVER.server_port
            
            logger.info(f"🚀 Flask сервер запущен на http://127.0.0.1:{SERVER_PORT}")
            _WSGI_SERVER.serve_forever()
    
    def start(self):
        """Запуск desktop приложения"""
        global SERVER_PORT
        
        # Создаем Flask приложение
        self.create_flask_app()
        
        # Запускаем Flask сервер в отдельном потоке
        self.server_thread = threading.Thread(target=self.start_flask_server, daemon=True)
        self.server_thread.start()
        
        # Ожидание инициализации сервера
        for _ in range(100):
            if SERVER_PORT:
                break
            time.sleep(0.05)
        
        # Создаем окно pywebview с динамическим URL
        self.window = webview.create_window(
            'VPN Server Manager - Clean',
            f'http://127.0.0.1:{SERVER_PORT}',  # Динамический порт!
            width=1200,
            height=800,
            resizable=True
        )
        
        # Обработчик закрытия
        self.window.events.closing += self.on_closing
        
        webview.start()
    
    def on_closing(self):
        """Graceful shutdown"""
        global SERVER_PORT, _WSGI_SERVER
        if SERVER_PORT and _WSGI_SERVER:
            _WSGI_SERVER.shutdown()

# run.py (v4.0.3 с версией из config.json)
import sys
import os
import socket
import logging

def find_free_port(start_port=5000, max_attempts=100):
    """Находит свободный порт для web режима"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find free port")

def main():
    if '--desktop' in sys.argv:
        # Desktop режим (порт автоматический)
        from desktop.window import DesktopApp
        config_name = 'development' if '--debug' in sys.argv else 'production'
        app = DesktopApp(config_name)
        app.start()
    else:
        # Web режим (динамический порт)
        from app import create_app
        config_name = 'development' if '--debug' in sys.argv else 'production'
        app = create_app(config_name)
        
        port = find_free_port(5000)
        
        # Загружаем версию из config.json
        import json
        version = "4.0.3"
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                version = config['app_info']['version']
        except:
            pass
        
        print(f"\n🌐 VPN Server Manager v{version}")
        print(f"📡 Web server: http://127.0.0.1:{port}\n")
        
        app.run(host='127.0.0.1', port=port, debug=(config_name == 'development'))

if __name__ == '__main__':
    main()
```
8. Работа с внешними API (requests)
ПРИНЦИП: Изолируйте HTTP-запросы в отдельный сервис с retry-логикой.

python
# app/services/api_service.py
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Optional

class APIService:
    """Сервис для работы с внешними API"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Создание сессии с retry-логикой"""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """GET запрос"""
        url = f"{self.base_url}/{endpoint}"
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
9. Безопасность
ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА:

Никогда не храните секреты в коде - используйте .env
Валидируйте все входные данные
Используйте HTTPS в production
Применяйте CSP headers
Шифруйте чувствительные данные с помощью cryptography
python
# app/utils/validators.py
from werkzeug.security import check_password_hash, generate_password_hash

def validate_password(password: str) -> bool:
    """Валидация пароля"""
    return (
        len(password) >= 8 and
        any(c.isupper() for c in password) and
        any(c.isdigit() for c in password)
    )

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return generate_password_hash(password, method='pbkdf2:sha256')
10. Логирование
ПРИНЦИП: Структурированное логирование на всех уровнях.

python
# app/__init__.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(app):
    if not app.debug:
        file_handler = RotatingFileHandler(
            'logs/app.log',
            maxBytes=10240000,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application startup')
11. Тестирование
ОБЯЗАТЕЛЬНО: Покрывайте тестами критичную функциональность.

python
# tests/conftest.py
import pytest
from app import create_app

@pytest.fixture
def app():
    app = create_app('testing')
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

# tests/test_services/test_crypto_service.py
from app.services.crypto_service import CryptoService

def test_encryption_decryption():
    service = CryptoService()
    key = service.generate_key()
    
    original = "secret data"
    encrypted = service.encrypt(original, key)
    decrypted = service.decrypt(encrypted, key)
    
    assert decrypted == original
    assert encrypted != original
## 12. Dependency Injection (Service Registry)

**ПРИНЦИП**: Используйте DI для управления зависимостями сервисов.

**v4.0.3**: Все сервисы регистрируются в `ServiceRegistry` при инициализации приложения.

```python
# app/services/__init__.py
class ServiceRegistry:
    """Реестр сервисов для Dependency Injection"""
    _services = {}
    
    @classmethod
    def register(cls, name: str, service):
        """Регистрация сервиса"""
        cls._services[name] = service
    
    @classmethod
    def get(cls, name: str):
        """Получение сервиса"""
        return cls._services.get(name)
    
    @classmethod
    def clear(cls):
        """Очистка реестра (для тестов)"""
        cls._services = {}

registry = ServiceRegistry()

# app/__init__.py (регистрация при создании приложения)
def register_services(app):
    """Регистрация всех сервисов"""
    from .services.ssh_service import SSHService
    from .services.crypto_service import CryptoService
    from .services.api_service import APIService
    from .services.data_manager_service import DataManagerService
    
    # Базовые сервисы
    registry.register('ssh', SSHService())
    registry.register('crypto', CryptoService())
    registry.register('api', APIService())
    
    # DataManagerService с зависимостями
    secret_key = app.config.get('SECRET_KEY')
    app_data_dir = app.config.get('APP_DATA_DIR')
    if secret_key and app_data_dir:
        registry.register('data_manager', DataManagerService(secret_key, app_data_dir))

# Использование в routes
from app.services import registry

@main_bp.route('/servers')
def list_servers():
    data_manager = registry.get('data_manager')
    servers = data_manager.load_servers(current_app.config)
    return render_template('index.html', servers=servers)
```
Контрольный список (Checklist)
 Application Factory реализован
 Все секреты в .env
 Blueprints для модульности
 Service Layer для бизнес-логики
 Кастомные исключения и обработчики
 Flask-Babel настроен
 Валидация входных данных
 Логирование настроено
 Тесты написаны
 Документация актуальна
 .gitignore содержит .env, __pycache__, etc.
 Requirements.txt актуален
Команды для работы
bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt

# Инициализация переводов
pybabel extract -F babel.cfg -o messages.pot .
pybabel init -i messages.pot -d app/translations -l ru
pybabel compile -d app/translations

# Запуск тестов
pytest

# Запуск приложения
python run.py              # Web режим
python run.py --desktop    # Desktop режим
Примечания
Всегда следуйте PEP 8
Используйте type hints (Python 3.10+)
Документируйте публичные методы docstrings
Версионируйте API endpoints
Регулярно обновляйте зависимости (pip-audit)
