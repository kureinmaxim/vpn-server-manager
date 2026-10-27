import pytest
import tempfile
import os
import shutil
from app import create_app
from app.services import registry

@pytest.fixture(autouse=True)
def isolated_ssh_home(monkeypatch, tmp_path):
    """Tests must never consult the developer's SSH keys or trust store."""
    monkeypatch.setenv('HOME', str(tmp_path))

@pytest.fixture
def app():
    """Создание тестового приложения"""
    # Создаем временную директорию для тестов
    test_dir = tempfile.mkdtemp()
    
    # Создаем тестовое приложение
    app = create_app('testing')
    
    # Настраиваем тестовые директории
    app.config['APP_DATA_DIR'] = test_dir
    app.config['DATA_DIR'] = os.path.join(test_dir, 'data')
    app.config['UPLOAD_FOLDER'] = os.path.join(test_dir, 'uploads')
    app.config['LOG_FILE'] = os.path.join(test_dir, 'test.log')
    app.config['DEFAULT_PIN'] = '1234'
    
    # Создаем необходимые директории
    os.makedirs(app.config['DATA_DIR'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    with app.app_context():
        yield app
    
    # Очищаем временные файлы
    shutil.rmtree(test_dir, ignore_errors=True)

@pytest.fixture
def client(app):
    """Тестовый клиент"""
    from flask.testing import FlaskClient
    from werkzeug.datastructures import Headers
    import secrets

    class BrowserClient(FlaskClient):
        """Emulate the shared form/fetch CSRF layer; csrf=False tests raw requests."""
        def open(self, *args, **kwargs):
            protect = kwargs.pop('csrf', True)
            if protect and kwargs.get('method', 'GET').upper() in ('POST', 'PUT', 'PATCH', 'DELETE'):
                with self.session_transaction() as state:
                    token = state.setdefault('csrf_token', secrets.token_urlsafe(32))
                headers = Headers(kwargs.get('headers'))
                if 'X-CSRF-Token' not in headers:
                    headers['X-CSRF-Token'] = token
                kwargs['headers'] = headers
            return super().open(*args, **kwargs)

    return BrowserClient(app)

@pytest.fixture
def runner(app):
    """Тестовый runner для CLI команд"""
    return app.test_cli_runner()

@pytest.fixture
def auth_headers(client):
    """Заголовки для аутентификации"""
    # Здесь можно добавить логику получения токенов аутентификации
    return {}

@pytest.fixture
def sample_server_data():
    """Тестовые данные сервера"""
    return {
        'id': 'test-server-1',
        'name': 'Test Server',
        'hostname': '192.168.1.100',
        'username': 'testuser',
        'password': 'testpass',
        'port': 22,
        'description': 'Test server for unit tests'
    }

@pytest.fixture
def sample_encrypted_data():
    """Тестовые зашифрованные данные"""
    return {
        'encrypted_servers': 'encrypted_data_here',
        'key': 'test_key_here'
    }

@pytest.fixture(autouse=True)
def clear_registry():
    """Очистка реестра сервисов перед каждым тестом"""
    registry.clear()
    yield
    registry.clear()


@pytest.fixture
def all_features(app):
    """Все необязательные кнопки главной включены (в новой установке «Проекты» и «Боты» скрыты)."""
    from app.services.ui_preferences import DEFAULT_FEATURES, save_ui_features
    save_ui_features(app, DEFAULT_FEATURES)
    return app
