import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Явным образом находим и загружаем .env, особенно для собранных приложений
is_frozen = getattr(sys, 'frozen', False)
if is_frozen:
    # В frozen режиме .env должен быть в APP_DATA_DIR
    # Сначала определяем APP_DATA_DIR
    app_name = "VPNServerManager-Clean"
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
    
    os.makedirs(app_data_dir, exist_ok=True)
    dotenv_path = os.path.join(app_data_dir, '.env')
    
    # Если .env не существует, создаем его с новым ключом
    if not os.path.exists(dotenv_path):
        from cryptography.fernet import Fernet
        secret_key = Fernet.generate_key().decode()
        
        # Копируем шаблон из бандла если есть
        bundle_env_example = os.path.join(getattr(sys, '_MEIPASS', '.'), 'env.example')
        if os.path.exists(bundle_env_example):
            import shutil
            shutil.copy2(bundle_env_example, dotenv_path)
            # Заменяем SECRET_KEY в скопированном файле
            with open(dotenv_path, 'r') as f:
                content = f.read()
            content = content.replace(
                'SECRET_KEY=your-secret-key-here-change-in-production',
                f'SECRET_KEY={secret_key}'
            )
            with open(dotenv_path, 'w') as f:
                f.write(content)
            print(f"✅ Created .env with new SECRET_KEY at {dotenv_path}")
        else:
            # Создаем минимальный .env
            with open(dotenv_path, 'w') as f:
                f.write(f"SECRET_KEY={secret_key}\n")
                f.write("APP_VERSION=4.0.9\n")
                f.write("BABEL_DEFAULT_LOCALE=ru\n")
            print(f"✅ Created minimal .env at {dotenv_path}")
    
    load_dotenv(dotenv_path=dotenv_path)
else:
    # В режиме разработки ищем .env в корне проекта
    load_dotenv()


def get_app_data_dir():
    """
    Возвращает директорию для хранения пользовательских данных приложения.
    Учитывает различие между режимом разработки и запакованным приложением.
    """
    # Определяем, запущено ли приложение как пакет
    is_frozen = getattr(sys, 'frozen', False)
    
    # Имя директории приложения
    app_name = "VPNServerManager-Clean"
    
    if is_frozen:  # Приложение запущено как .app или .exe
        if sys.platform == 'darwin':  # macOS
            # ~/Library/Application Support/VPNServerManager
            app_data_dir = os.path.join(
                os.path.expanduser("~"), 
                "Library", "Application Support", 
                app_name
            )
        elif sys.platform == 'win32':  # Windows
            # %APPDATA%\VPNServerManager
            app_data_dir = os.path.join(
                os.getenv('APPDATA', os.path.expanduser("~")),
                app_name
            )
        else:  # Linux и другие Unix-подобные системы
            # ~/.local/share/VPNServerManager
            app_data_dir = os.path.join(
                os.path.expanduser("~"),
                ".local", "share",
                app_name
            )
    else:  # Режим разработки
        # Используем директорию проекта
        app_data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Создаем директорию, если её нет
    os.makedirs(app_data_dir, exist_ok=True)
    return app_data_dir

class Config:
    """Базовая конфигурация"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    BABEL_DEFAULT_LOCALE = os.getenv('BABEL_DEFAULT_LOCALE', 'ru')
    BABEL_TRANSLATION_DIRECTORIES = 'translations'
    BABEL_SUPPORTED_LOCALES = ['ru', 'en', 'zh']
    
    # Настройки приложения
    APP_VERSION = os.getenv('APP_VERSION', '4.0.9')
    APP_NAME = 'VPNServerManager-Clean'
    APP_DATA_DIR = get_app_data_dir()
    
    # Allowed extensions
    ALLOWED_EXTENSIONS = {'enc', 'env', 'txt', 'zip', 'json'}
    
    # Настройки данных - используем APP_DATA_DIR для всех путей
    DATA_DIR = os.path.join(APP_DATA_DIR, 'data')
    SERVERS_FILE = os.getenv('SERVERS_FILE', 'servers.json.enc')
    HINTS_FILE = os.getenv('HINTS_FILE', 'hints.json')
    
    # Настройки PIN
    DEFAULT_PIN = os.getenv('DEFAULT_PIN', '1234')
    
    # API URLs
    IP_CHECK_API = os.getenv('IP_CHECK_API', 'https://ipinfo.io/{ip}/json')
    GENERAL_IP_TEST = os.getenv('GENERAL_IP_TEST', 'https://browserleaks.com/ip')
    GENERAL_DNS_TEST = os.getenv('GENERAL_DNS_TEST', 'https://dnsleaktest.com/')
    IP2LOCATION_DEMO = os.getenv('IP2LOCATION_DEMO', 'https://www.ip2location.com/demo/{ip}')
    
    # Настройки загрузки файлов - используем APP_DATA_DIR
    UPLOAD_FOLDER = os.path.join(APP_DATA_DIR, 'uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '16777216'))  # 16MB
    
    # Настройки логирования
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    # Используем правильный путь для логов в зависимости от режима
    _is_frozen = getattr(sys, 'frozen', False)
    if _is_frozen and sys.platform == 'darwin':
        # macOS frozen: ~/Library/Logs/VPNServerManager-Clean/
        LOG_FILE = os.path.join(
            os.path.expanduser("~"),
            "Library", "Logs", "VPNServerManager-Clean",
            "app.log"
        )
    else:
        # Dev mode: logs/ в директории проекта
        LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    
    @staticmethod
    def init_app(app):
        """Инициализация приложения с конфигурацией"""
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    # Дополнительные настройки production
    LOG_LEVEL = 'WARNING'

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    # Используем временные файлы для тестов
    DATA_DIR = 'test_data'
    SERVERS_FILE = 'test_servers.json.enc'
    
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}
