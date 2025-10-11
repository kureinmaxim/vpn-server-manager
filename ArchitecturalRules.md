Content is user-generated and unverified.
Архитектурные правила для Flask-приложения
Контекст проекта
Разработка Flask-приложения с desktop GUI (pywebview), поддержкой интернационализации, SSH/SFTP функциональностью и криптографией.

Структура проекта
project_root/
├── app/
│   ├── __init__.py              # Application Factory
│   ├── config.py                # Конфигурация приложения
│   ├── models/                  # Модели данных
│   │   ├── __init__.py
│   │   └── user.py
│   ├── services/                # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── ssh_service.py       # Paramiko сервисы
│   │   ├── crypto_service.py    # Cryptography сервисы
│   │   └── api_service.py       # Requests сервисы
│   ├── routes/                  # Маршруты (blueprints)
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── api.py
│   ├── templates/               # Jinja2 шаблоны
│   │   ├── base.html
│   │   └── index.html
│   ├── static/                  # Статические файлы
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   ├── translations/            # Flask-Babel переводы
│   │   ├── en/
│   │   └── ru/
│   ├── utils/                   # Утилиты
│   │   ├── __init__.py
│   │   ├── validators.py
│   │   └── decorators.py
│   └── exceptions.py            # Кастомные исключения
├── desktop/
│   ├── __init__.py
│   └── window.py                # pywebview конфигурация
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_services/
│   └── test_routes/
├── migrations/                   # Если используется Flask-Migrate
├── .env.example
├── .env
├── .gitignore
├── requirements.txt
├── babel.cfg                     # Babel конфигурация
├── run.py                        # Точка входа
└── README.md
1. Application Factory Pattern
ОБЯЗАТЕЛЬНО: Используйте паттерн Application Factory для создания Flask-приложения.

python
# app/__init__.py
from flask import Flask
from flask_babel import Babel
from .config import config_by_name

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    
    # Инициализация расширений
    babel = Babel(app)
    
    # Регистрация blueprints
    from .routes import main_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Обработчики ошибок
    register_error_handlers(app)
    
    return app
2. Конфигурация через переменные окружения
ПРАВИЛО: Все чувствительные данные и настройки окружения хранятся в .env файле.

python
# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Базовая конфигурация"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    BABEL_DEFAULT_LOCALE = os.getenv('BABEL_DEFAULT_LOCALE', 'en')
    BABEL_TRANSLATION_DIRECTORIES = 'translations'
    
class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    # Дополнительные настройки production

class TestingConfig(Config):
    TESTING = True
    
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}
3. Слой сервисов (Service Layer)
ПРИНЦИП: Вся бизнес-логика изолирована в отдельном слое сервисов.

python
# app/services/ssh_service.py
import paramiko
from typing import Optional, Dict
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
    
    def disconnect(self) -> None:
        """Закрытие соединения"""
        if self.client:
            self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
python
# app/services/crypto_service.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
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
7. Desktop GUI с pywebview
АРХИТЕКТУРА: Разделяйте web и desktop слои.

python
# desktop/window.py
import webview
from app import create_app

class DesktopApp:
    def __init__(self):
        self.app = create_app('production')
        
    def start(self):
        """Запуск desktop приложения"""
        webview.create_window(
            'Application Name',
            self.app,
            width=1200,
            height=800,
            resizable=True
        )
        webview.start()

# run.py
if __name__ == '__main__':
    import sys
    if '--desktop' in sys.argv:
        from desktop.window import DesktopApp
        app = DesktopApp()
        app.start()
    else:
        from app import create_app
        app = create_app()
        app.run()
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
12. Dependency Injection
ПРИНЦИП: Используйте DI для управления зависимостями сервисов.

python
# app/services/__init__.py
class ServiceRegistry:
    """Реестр сервисов"""
    _services = {}
    
    @classmethod
    def register(cls, name: str, service):
        cls._services[name] = service
    
    @classmethod
    def get(cls, name: str):
        return cls._services.get(name)

# Инициализация
registry = ServiceRegistry()
registry.register('ssh', SSHService())
registry.register('crypto', CryptoService())
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
