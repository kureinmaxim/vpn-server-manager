from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from datetime import datetime
import json

@dataclass
class Server:
    """Модель сервера"""
    id: str
    name: str
    hostname: str
    username: str
    password: Optional[str] = None
    key_file: Optional[str] = None
    port: int = 22
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True
    last_connection: Optional[datetime] = None
    connection_status: str = 'unknown'  # 'connected', 'disconnected', 'error', 'unknown'
    
    def __post_init__(self):
        """Инициализация после создания объекта"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        data = asdict(self)
        # Преобразуем datetime объекты в строки
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Server':
        """Создание объекта из словаря"""
        # Преобразуем строки обратно в datetime объекты
        for key in ['created_at', 'updated_at', 'last_connection']:
            if key in data and data[key]:
                try:
                    data[key] = datetime.fromisoformat(data[key])
                except (ValueError, TypeError):
                    data[key] = None
        
        return cls(**data)
    
    def to_json(self) -> str:
        """Преобразование в JSON строку"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Server':
        """Создание объекта из JSON строки"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def update(self, **kwargs) -> None:
        """Обновление полей сервера"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
    
    def validate(self) -> list:
        """Валидация данных сервера"""
        errors = []
        
        if not self.name or len(self.name.strip()) == 0:
            errors.append("Server name is required")
        
        if not self.hostname or len(self.hostname.strip()) == 0:
            errors.append("Hostname is required")
        
        if not self.username or len(self.username.strip()) == 0:
            errors.append("Username is required")
        
        if not self.password and not self.key_file:
            errors.append("Either password or key file is required")
        
        if self.port < 1 or self.port > 65535:
            errors.append("Port must be between 1 and 65535")
        
        if len(self.name) > 100:
            errors.append("Server name is too long (max 100 characters)")
        
        return errors
    
    def is_valid(self) -> bool:
        """Проверка валидности данных"""
        return len(self.validate()) == 0
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Получение информации для подключения"""
        return {
            'hostname': self.hostname,
            'username': self.username,
            'password': self.password,
            'key_file': self.key_file,
            'port': self.port
        }
    
    def get_display_name(self) -> str:
        """Получение отображаемого имени"""
        return f"{self.name} ({self.hostname})"
    
    def __str__(self) -> str:
        return self.get_display_name()
    
    def __repr__(self) -> str:
        return f"Server(id='{self.id}', name='{self.name}', hostname='{self.hostname}')"

@dataclass
class ServerConnection:
    """Модель подключения к серверу"""
    server_id: str
    connected_at: datetime
    disconnected_at: Optional[datetime] = None
    status: str = 'connected'  # 'connected', 'disconnected', 'error'
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServerConnection':
        """Создание объекта из словаря"""
        for key in ['connected_at', 'disconnected_at']:
            if key in data and data[key]:
                try:
                    data[key] = datetime.fromisoformat(data[key])
                except (ValueError, TypeError):
                    data[key] = None
        
        return cls(**data)

@dataclass
class ServerStats:
    """Статистика сервера"""
    server_id: str
    total_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    last_successful_connection: Optional[datetime] = None
    last_failed_connection: Optional[datetime] = None
    average_connection_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServerStats':
        """Создание объекта из словаря"""
        for key in ['last_successful_connection', 'last_failed_connection']:
            if key in data and data[key]:
                try:
                    data[key] = datetime.fromisoformat(data[key])
                except (ValueError, TypeError):
                    data[key] = None
        
        return cls(**data)
