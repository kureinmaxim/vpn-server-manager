import pytest
import tempfile
import os
import shutil
from app import create_app
from app.services import registry

@pytest.fixture
def app():
    """Создание тестового приложения"""
    # Создаем временную директорию для тестов
    test_dir = tempfile.mkdtemp()
    
    # Создаем тестовое приложение
    app = create_app('testing')
    
    # Настраиваем тестовые директории
    app.config['DATA_DIR'] = os.path.join(test_dir, 'data')
    app.config['UPLOAD_FOLDER'] = os.path.join(test_dir, 'uploads')
    app.config['LOG_FILE'] = os.path.join(test_dir, 'test.log')
    
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
    return app.test_client()

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
