import re
import socket
from typing import Optional, List, Dict, Any
from werkzeug.security import check_password_hash, generate_password_hash
from ..exceptions import ValidationError

class Validators:
    """Класс для валидации различных типов данных"""
    
    @staticmethod
    def validate_password(password: str, min_length: int = 8) -> bool:
        """Валидация пароля"""
        if not password or len(password) < min_length:
            return False
        
        # Проверяем наличие заглавной буквы
        if not any(c.isupper() for c in password):
            return False
        
        # Проверяем наличие цифры
        if not any(c.isdigit() for c in password):
            return False
        
        # Проверяем наличие специального символа
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False
        
        return True
    
    @staticmethod
    def validate_pin(pin: str, length: int = 4) -> bool:
        """Валидация PIN кода"""
        if not pin or len(pin) != length:
            return False
        
        # PIN должен содержать только цифры
        return pin.isdigit()
    
    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """Валидация IP адреса"""
        try:
            socket.inet_aton(ip)
            return True
        except socket.error:
            return False
    
    @staticmethod
    def validate_hostname(hostname: str) -> bool:
        """Валидация имени хоста"""
        if not hostname or len(hostname) > 253:
            return False
        
        # Проверяем формат hostname
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(pattern, hostname))
    
    @staticmethod
    def validate_port(port: int) -> bool:
        """Валидация порта"""
        return 1 <= port <= 65535
    
    @staticmethod
    def validate_ssh_credentials(hostname: str, username: str, 
                                password: Optional[str] = None,
                                key_file: Optional[str] = None) -> List[str]:
        """Валидация SSH учетных данных"""
        errors = []
        
        if not hostname:
            errors.append("Hostname is required")
        elif not (Validators.validate_ip_address(hostname) or Validators.validate_hostname(hostname)):
            errors.append("Invalid hostname or IP address")
        
        if not username:
            errors.append("Username is required")
        elif len(username) < 1 or len(username) > 32:
            errors.append("Username must be 1-32 characters long")
        
        if not password and not key_file:
            errors.append("Either password or key file is required")
        
        if key_file and not os.path.exists(key_file):
            errors.append("Key file does not exist")
        
        return errors
    
    @staticmethod
    def validate_server_data(server_data: Dict[str, Any]) -> List[str]:
        """Валидация данных сервера"""
        errors = []
        
        required_fields = ['name', 'hostname', 'username']
        for field in required_fields:
            if field not in server_data or not server_data[field]:
                errors.append(f"Field '{field}' is required")
        
        if 'hostname' in server_data and server_data['hostname']:
            if not (Validators.validate_ip_address(server_data['hostname']) or 
                   Validators.validate_hostname(server_data['hostname'])):
                errors.append("Invalid hostname or IP address")
        
        if 'port' in server_data and server_data['port']:
            try:
                port = int(server_data['port'])
                if not Validators.validate_port(port):
                    errors.append("Invalid port number")
            except (ValueError, TypeError):
                errors.append("Port must be a number")
        
        if 'name' in server_data and server_data['name']:
            if len(server_data['name']) > 100:
                errors.append("Server name is too long (max 100 characters)")
        
        return errors
    
    @staticmethod
    def validate_file_upload(filename: str, allowed_extensions: List[str] = None,
                           max_size: int = 16 * 1024 * 1024) -> List[str]:
        """Валидация загружаемого файла"""
        errors = []
        
        if not filename:
            errors.append("No file selected")
            return errors
        
        if allowed_extensions:
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            if file_ext not in allowed_extensions:
                errors.append(f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}")
        
        # Проверка размера файла (если файл уже загружен)
        # В реальном приложении это будет проверяться в route handler
        
        return errors
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Очистка имени файла от опасных символов"""
        # Удаляем опасные символы
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Удаляем пробелы в начале и конце
        filename = filename.strip()
        # Ограничиваем длину
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        
        return filename
    
    @staticmethod
    def validate_json_data(data: str) -> bool:
        """Валидация JSON данных"""
        try:
            import json
            json.loads(data)
            return True
        except (json.JSONDecodeError, TypeError):
            return False

# Функции для работы с паролями
def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return generate_password_hash(password, method='pbkdf2:sha256')

def check_password(password_hash: str, password: str) -> bool:
    """Проверка пароля"""
    return check_password_hash(password_hash, password)

# Функции для работы с файлами
import os

def get_file_extension(filename: str) -> str:
    """Получение расширения файла"""
    return os.path.splitext(filename)[1].lower()

def get_file_size(file_path: str) -> int:
    """Получение размера файла"""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0

def is_safe_path(base_path: str, path: str) -> bool:
    """Проверка безопасности пути (защита от directory traversal)"""
    try:
        base_path = os.path.abspath(base_path)
        path = os.path.abspath(path)
        return path.startswith(base_path)
    except (OSError, ValueError):
        return False
