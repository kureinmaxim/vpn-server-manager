class AppException(Exception):
    """Базовое исключение приложения"""
    status_code = 500
    
    def __init__(self, message, status_code=None, payload=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

class SSHConnectionError(AppException):
    """Ошибка SSH соединения"""
    status_code = 503

class CryptoError(AppException):
    """Ошибка криптографических операций"""
    status_code = 500

class ValidationError(AppException):
    """Ошибка валидации данных"""
    status_code = 400

class FileNotFoundError(AppException):
    """Ошибка файла не найден"""
    status_code = 404

class AuthenticationError(AppException):
    """Ошибка аутентификации"""
    status_code = 401

class APIError(AppException):
    """Ошибка внешнего API"""
    status_code = 502

class ConfigurationError(AppException):
    """Ошибка конфигурации"""
    status_code = 500
