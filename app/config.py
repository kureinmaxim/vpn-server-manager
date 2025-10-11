import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Базовая конфигурация"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    BABEL_DEFAULT_LOCALE = os.getenv('BABEL_DEFAULT_LOCALE', 'ru')
    BABEL_TRANSLATION_DIRECTORIES = 'translations'
    BABEL_SUPPORTED_LOCALES = ['ru', 'en', 'zh']
    
    # Настройки приложения
    APP_VERSION = os.getenv('APP_VERSION', '4.0.0')
    APP_NAME = 'VPNServerManager-Clean'
    
    # Настройки данных
    DATA_DIR = os.getenv('DATA_DIR', 'data')
    SERVERS_FILE = os.getenv('SERVERS_FILE', 'servers.json.enc')
    HINTS_FILE = os.getenv('HINTS_FILE', 'hints.json')
    
    # Настройки PIN
    DEFAULT_PIN = os.getenv('DEFAULT_PIN', '1234')
    
    # API URLs
    IP_CHECK_API = os.getenv('IP_CHECK_API', 'https://ipinfo.io/{ip}/json')
    GENERAL_IP_TEST = os.getenv('GENERAL_IP_TEST', 'https://browserleaks.com/ip')
    GENERAL_DNS_TEST = os.getenv('GENERAL_DNS_TEST', 'https://dnsleaktest.com/')
    IP2LOCATION_DEMO = os.getenv('IP2LOCATION_DEMO', 'https://www.ip2location.com/demo/{ip}')
    
    # Настройки загрузки файлов
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '16777216'))  # 16MB
    
    # Настройки логирования
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
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
