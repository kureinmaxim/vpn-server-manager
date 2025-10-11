"""
Data Management Service
Сервис для управления данными приложения: экспорт, импорт, шифрование.
"""

import os
import sys
import json
import shutil
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from cryptography.fernet import Fernet, InvalidToken


class DataManagerService:
    """Сервис для управления данными приложения"""
    
    def __init__(self, secret_key: str, app_data_dir: str):
        """
        Инициализация сервиса управления данными
        
        Args:
            secret_key: Ключ шифрования Fernet
            app_data_dir: Директория для хранения данных приложения
        """
        self.secret_key = secret_key
        self.app_data_dir = app_data_dir
        self.fernet = Fernet(secret_key.encode())
        
    def get_export_dir(self) -> str:
        """
        Возвращает безопасную директорию для экспорта файлов.
        Использует папку Downloads пользователя.
        """
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.exists(downloads_dir) and os.access(downloads_dir, os.W_OK):
            return downloads_dir
        # Если Downloads недоступна, используем app_data_dir
        return self.app_data_dir
    
    def get_active_data_path(self, config: Dict[str, Any]) -> Optional[str]:
        """
        Возвращает полный путь к активному файлу данных из конфигурации.
        
        Args:
            config: Конфигурация приложения Flask
            
        Returns:
            Полный путь к файлу данных или None
        """
        path = config.get('active_data_file')
        if path:
            # Если путь относительный, сделать его абсолютным
            if not os.path.isabs(path):
                return os.path.join(self.app_data_dir, path)
            return path
        return None
    
    def encrypt_data(self, data: str) -> str:
        """
        Шифрует данные с помощью Fernet
        
        Args:
            data: Строка для шифрования
            
        Returns:
            Зашифрованная строка
        """
        if not data:
            return ""
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data: Any) -> str:
        """
        Расшифровывает данные, зашифрованные с помощью Fernet.
        Автоматически определяет формат данных и обрабатывает их соответственно.
        
        Args:
            encrypted_data: Зашифрованные данные (str, bytes или другой тип)
            
        Returns:
            Расшифрованная строка
        """
        # Проверяем на пустые данные
        if not encrypted_data or encrypted_data == "" or encrypted_data is None:
            return ""
        
        # Конвертируем в строку если нужно
        if not isinstance(encrypted_data, str):
            encrypted_data = str(encrypted_data)
        
        # Дополнительная проверка на пустую строку после конвертации
        if encrypted_data.strip() == "":
            return ""
        
        # Если данные начинаются с gAAAAA, это точно Fernet данные
        if encrypted_data.startswith('gAAAAA'):
            try:
                return self.fernet.decrypt(encrypted_data.encode()).decode()
            except InvalidToken:
                return encrypted_data
        
        # Если не похоже на зашифрованные данные, возвращаем как есть
        return encrypted_data
    
    def load_servers(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Загружает и расшифровывает серверы из активного зашифрованного файла.
        
        Args:
            config: Конфигурация приложения Flask
            
        Returns:
            Список серверов
        """
        active_file = self.get_active_data_path(config)
        if not active_file:
            return []
        
        if not os.path.exists(active_file):
            return []

        try:
            with open(active_file, 'rb') as f:
                encrypted_data = f.read()

            if not encrypted_data:
                return []

            decrypted_data = self.fernet.decrypt(encrypted_data)
            servers = json.loads(decrypted_data.decode('utf-8'))
            return servers if isinstance(servers, list) else []
        except Exception as e:
            print(f"Ошибка загрузки серверов: {e}")
            return []
    
    def save_servers(self, servers: List[Dict[str, Any]], file_path: str) -> None:
        """
        Сохраняет серверы в зашифрованный файл.
        
        Args:
            servers: Список серверов для сохранения
            file_path: Путь к файлу для сохранения
        """
        # Создаем директорию если нужно
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Шифруем данные
        json_string = json.dumps(servers, ensure_ascii=False, indent=2)
        encrypted_data = self.fernet.encrypt(json_string.encode('utf-8'))
        
        # Сохраняем
        with open(file_path, 'wb') as f:
            f.write(encrypted_data)
    
    def create_backup(self, source_file: str, backup_dir: str, prefix: str = "backup") -> str:
        """
        Создает резервную копию файла с временной меткой.
        
        Args:
            source_file: Исходный файл для копирования
            backup_dir: Директория для сохранения резервной копии
            prefix: Префикс имени файла
            
        Returns:
            Путь к созданной резервной копии
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{prefix}_{timestamp}.enc"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        os.makedirs(backup_dir, exist_ok=True)
        shutil.copy2(source_file, backup_path)
        
        return backup_path
    
    def verify_key_for_file(self, file_content: bytes, test_key: str) -> Dict[str, Any]:
        """
        Проверяет, подходит ли ключ для расшифровки файла.
        
        Args:
            file_content: Содержимое зашифрованного файла
            test_key: Ключ для проверки
            
        Returns:
            Словарь с результатами проверки
        """
        result = {
            'success': False,
            'error': None,
            'data': None
        }
        
        try:
            test_fernet = Fernet(test_key.encode())
            decrypted_data = test_fernet.decrypt(file_content).decode()
            data = json.loads(decrypted_data)
            
            result['success'] = True
            result['data'] = data
            
            # Анализируем содержимое
            if isinstance(data, list):
                result['server_count'] = len(data)
                
                providers = set()
                server_names = []
                
                for server in data:
                    if isinstance(server, dict):
                        if 'provider' in server:
                            providers.add(server['provider'])
                        if 'name' in server:
                            server_names.append(server['name'])
                
                result['providers'] = sorted(providers) if providers else []
                result['server_names'] = server_names
                
        except InvalidToken:
            result['error'] = 'invalid_key'
        except json.JSONDecodeError:
            result['error'] = 'invalid_json'
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def re_encrypt_password(self, encrypted_password: str, old_key: str, new_key: str) -> str:
        """
        Перешифровывает пароль с одного ключа на другой.
        
        Args:
            encrypted_password: Зашифрованный пароль
            old_key: Старый ключ шифрования
            new_key: Новый ключ шифрования
            
        Returns:
            Пароль, зашифрованный новым ключом
        """
        try:
            old_fernet = Fernet(old_key.encode())
            new_fernet = Fernet(new_key.encode())
            
            # Расшифровываем старым ключом
            decrypted = old_fernet.decrypt(encrypted_password.encode()).decode()
            
            # Шифруем новым ключом
            return new_fernet.encrypt(decrypted.encode()).decode()
        except Exception:
            # Если не удалось перешифровать, возвращаем как есть
            return encrypted_password
    
    def merge_servers(self, current_servers: List[Dict[str, Any]], 
                     new_servers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Объединяет списки серверов, избегая дублирования.
        
        Args:
            current_servers: Текущий список серверов
            new_servers: Новые серверы для добавления
            
        Returns:
            Словарь с результатами объединения
        """
        # Получаем списки существующих IP адресов и имен
        existing_ips = {server.get('ip', '') for server in current_servers if server.get('ip')}
        existing_names = {server.get('name', '') for server in current_servers if server.get('name')}
        
        # Находим максимальный ID среди существующих серверов
        max_id = 0
        for server in current_servers:
            if 'id' in server and isinstance(server['id'], int):
                max_id = max(max_id, server['id'])
        
        # Фильтруем импортируемые сервера и присваиваем новые ID
        added_servers = []
        skipped_count = 0
        
        for server in new_servers:
            server_ip = server.get('ip', '')
            server_name = server.get('name', '')
            
            # Проверяем на дублирование по IP или имени
            if server_ip in existing_ips or server_name in existing_names:
                skipped_count += 1
                continue
            
            # Присваиваем новый уникальный ID
            max_id += 1
            server['id'] = max_id
            added_servers.append(server)
            
            # Добавляем в списки для отслеживания дублей
            if server_ip:
                existing_ips.add(server_ip)
            if server_name:
                existing_names.add(server_name)
        
        return {
            'merged_servers': current_servers + added_servers,
            'added_count': len(added_servers),
            'skipped_count': skipped_count
        }
    
    def allowed_file(self, filename: str, allowed_extensions: set) -> bool:
        """
        Проверяет, разрешено ли расширение файла.
        
        Args:
            filename: Имя файла
            allowed_extensions: Множество разрешенных расширений
            
        Returns:
            True, если расширение разрешено
        """
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in allowed_extensions

