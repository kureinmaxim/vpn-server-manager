"""
Data Management Service
Сервис для управления данными приложения: экспорт, импорт, шифрование.
"""

import os
import sys
import json
import shutil
import copy
import datetime
import threading
from flask import g, has_request_context
from flask_babel import gettext as _
from .vault_io import (VaultError, VaultConflict, ServersSnapshot, DnsSnapshot, canonical, revision, file_lock, atomic_write)
from pathlib import Path
from typing import Optional, List, Dict, Any
from cryptography.fernet import Fernet, InvalidToken

from ..utils.credentials import sanitize_secret

# Тип узла карточки: арендованный VPS, домашний NAS или ПК в mesh. Старые карточки — VPS.
SERVER_KINDS = ('vps', 'nas', 'pc')


def server_kind(server: Dict[str, Any]) -> str:
    kind = server.get('kind') if isinstance(server, dict) else None
    return kind if kind in SERVER_KINDS else 'vps'


def _extra_addresses(server: Dict[str, Any]) -> List[Dict[str, str]]:
    """Дополнительные адреса SSH (mesh, LAN, прямой). Повреждённый список не ломает загрузку."""
    from .ssh_address import AddressError, clean_addresses
    try:
        return clean_addresses(server.get('extra_addresses') or [], server.get('ip_address'))
    except AddressError:
        return []


class DataManagerService:
    """Сервис для управления данными приложения"""
    
    def __init__(self, secret_key: str, app_data_dir: str):
        """
        Инициализация сервиса управления данными
        
        Args:
            secret_key: Ключ шифрования Fernet
            app_data_dir: Директория для хранения данных приложения
        """
        import logging
        logger = logging.getLogger(__name__)
        
        self.secret_key = secret_key
        self.app_data_dir = app_data_dir
        self.fernet = Fernet(secret_key.encode())
        self._observations = threading.local()
        logger.info(f"DataManagerService initialized. APP_DATA_DIR: '{self.app_data_dir}'")
        
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
    
    def normalize_server_data(self, server: Dict[str, Any]) -> Dict[str, Any]:
        """
        Нормализует данные сервера, добавляя отсутствующие поля с дефолтными значениями.
        
        Args:
            server: Данные сервера для нормализации
            
        Returns:
            Нормализованные данные сервера
        """
        # Базовые поля верхнего уровня
        defaults = {
            'id': server.get('id', 0),
            'name': server.get('name', ''),
            'provider': server.get('provider', ''),
            'ip_address': server.get('ip_address', ''),
            'os': server.get('os', ''),
            'status': server.get('status', 'Active'),
            'notes': server.get('notes', ''),
            'card_color': server.get('card_color', '#ffc107'),
            'panel_url': server.get('panel_url', ''),
            'hoster_url': server.get('hoster_url', ''),
            'icon_filename': server.get('icon_filename', ''),
            'os_icon': server.get('os_icon', 'bi-server'),
            'docker_info': server.get('docker_info', ''),
            'software_info': server.get('software_info', ''),
            'archived': bool(server.get('archived', False)),
            'kind': server_kind(server),
            'extra_addresses': _extra_addresses(server),
        }
        
        # Вложенные объекты с дефолтными значениями
        if 'specs' not in server or not isinstance(server['specs'], dict):
            defaults['specs'] = {'cpu': '', 'ram': '', 'disk': ''}
        else:
            defaults['specs'] = {
                'cpu': server['specs'].get('cpu', ''),
                'ram': server['specs'].get('ram', ''),
                'disk': server['specs'].get('disk', '')
            }
        
        if 'payment_info' not in server or not isinstance(server['payment_info'], dict):
            defaults['payment_info'] = {
                'amount': 0.0,
                'currency': 'USD',
                'next_due_date': '',
                'payment_period': 'Monthly',
                'receipts': [],
                'formatted_date': 'N/A'
            }
        else:
            defaults['payment_info'] = {
                'amount': server['payment_info'].get('amount', 0.0),
                'currency': server['payment_info'].get('currency', 'USD'),
                'next_due_date': server['payment_info'].get('next_due_date', ''),
                'payment_period': server['payment_info'].get('payment_period', 'Monthly'),
                'receipts': server['payment_info'].get('receipts', []),
                'formatted_date': server['payment_info'].get('formatted_date', 'N/A')
            }
        
        if 'ssh_credentials' not in server or not isinstance(server['ssh_credentials'], dict):
            defaults['ssh_credentials'] = {
                'user': '',
                'password': '',
                'port': 22,
                'root_password': '',
                'root_login_allowed': False,
                'private_key': '',
                'key_passphrase': '',
                'key_hint': '',
                'key_path': '',
                'password_decrypted': '',
                'root_password_decrypted': ''
            }
        else:
            ssh = server['ssh_credentials']
            defaults['ssh_credentials'] = {
                'user': ssh.get('user', ''),
                'password': ssh.get('password', ''),
                'port': ssh.get('port', 22),
                'root_password': ssh.get('root_password', ''),
                'root_login_allowed': ssh.get('root_login_allowed', False),
                # SSH-ключ: зашифрованный путь или текст, фраза-пароль; отпечаток и путь — для показа
                'private_key': ssh.get('private_key', ''),
                'key_passphrase': ssh.get('key_passphrase', ''),
                'key_hint': ssh.get('key_hint', ''),
                'key_path': ssh.get('key_path', ''),
                'password_decrypted': ssh.get('password_decrypted', ''),
                'root_password_decrypted': ssh.get('root_password_decrypted', '')
            }
        
        if 'panel_credentials' not in server or not isinstance(server['panel_credentials'], dict):
            defaults['panel_credentials'] = {
                'user': '',
                'password': '',
                'user_decrypted': '',
                'password_decrypted': ''
            }
        else:
            panel = server['panel_credentials']
            defaults['panel_credentials'] = {
                'user': panel.get('user', ''),
                'password': panel.get('password', ''),
                'user_decrypted': panel.get('user_decrypted', ''),
                'password_decrypted': panel.get('password_decrypted', '')
            }
        
        if 'hoster_credentials' not in server or not isinstance(server['hoster_credentials'], dict):
            defaults['hoster_credentials'] = {
                'user': '',
                'password': '',
                'login_method': 'password',
                'user_decrypted': '',
                'password_decrypted': ''
            }
        else:
            hoster = server['hoster_credentials']
            defaults['hoster_credentials'] = {
                'user': hoster.get('user', ''),
                'password': hoster.get('password', ''),
                'login_method': hoster.get('login_method', 'password'),
                'user_decrypted': hoster.get('user_decrypted', ''),
                'password_decrypted': hoster.get('password_decrypted', '')
            }
        
        if 'geolocation' not in server or not isinstance(server['geolocation'], dict):
            defaults['geolocation'] = {
                'city': '',
                'country': '',
                'region': '',
                'ip': server.get('ip_address', '')
            }
        else:
            geo = server['geolocation']
            defaults['geolocation'] = {
                'city': geo.get('city', ''),
                'country': geo.get('country', ''),
                'region': geo.get('region', ''),
                'ip': geo.get('ip', server.get('ip_address', ''))
            }
        
        if 'checks' not in server or not isinstance(server['checks'], dict):
            defaults['checks'] = {'dns_ok': False, 'streaming_ok': False}
        else:
            defaults['checks'] = {
                'dns_ok': server['checks'].get('dns_ok', False),
                'streaming_ok': server['checks'].get('streaming_ok', False)
            }
        
        if 'hosting_analysis' not in server or not isinstance(server['hosting_analysis'], dict):
            defaults['hosting_analysis'] = {'text': 'N/A', 'quality': 'secondary'}
        else:
            defaults['hosting_analysis'] = {
                'text': server['hosting_analysis'].get('text', 'N/A'),
                'quality': server['hosting_analysis'].get('quality', 'secondary')
            }
        
        # Объединяем с оригинальными данными
        normalized = {**server, **defaults}
        
        return normalized
    
    def load_servers(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Загружает и расшифровывает серверы из активного зашифрованного файла.
        
        Args:
            config: Конфигурация приложения Flask
            
        Returns:
            Список серверов с расшифрованными паролями для отображения
        """
        active_file = self.get_active_data_path(config)
        if not active_file:
            return []
        
        try:
            servers, _dns = self.read_payload(active_file)
            source = servers
            
            # Нормализуем каждый сервер
            if isinstance(servers, list):
                servers = [self.normalize_server_data(server) for server in servers]
                
                # 🔑 Расшифровываем пароли для отображения в интерфейсе
                for server in servers:
                    # SSH credentials
                    if 'ssh_credentials' in server:
                        ssh = server['ssh_credentials']
                        ssh['password_decrypted'] = sanitize_secret(
                            self.decrypt_data(ssh.get('password', ''))
                        )
                        ssh['root_password_decrypted'] = sanitize_secret(
                            self.decrypt_data(ssh.get('root_password', ''))
                        )
                    
                    # Panel credentials
                    if 'panel_credentials' in server:
                        panel = server['panel_credentials']
                        panel['user_decrypted'] = sanitize_secret(
                            self.decrypt_data(panel.get('user', ''))
                        )
                        panel['password_decrypted'] = sanitize_secret(
                            self.decrypt_data(panel.get('password', ''))
                        )
                    
                    # Hoster credentials
                    if 'hoster_credentials' in server:
                        hoster = server['hoster_credentials']
                        hoster['user_decrypted'] = sanitize_secret(
                            self.decrypt_data(hoster.get('user', ''))
                        )
                        hoster['password_decrypted'] = sanitize_secret(
                            self.decrypt_data(hoster.get('password', ''))
                        )
            
            return ServersSnapshot(servers, source.vault_path, source.vault_revision)
        except (OSError, InvalidToken, ValueError, TypeError, KeyError) as exc:
            raise VaultError(_('Хранилище не прочитано. Проверьте ключ или восстановите резервную копию. Запись запрещена.')) from exc

    @staticmethod
    def split_payload(data: Any):
        """Разделяет содержимое файла на (серверы, DNS-реестр).

        Старый формат — JSON-список серверов; новый — {"servers": [...], "dns": {...}}.
        """
        if isinstance(data, dict) and isinstance(data.get('servers'), list):
            dns = data.get('dns', {})
            if not isinstance(dns, dict) or not all(isinstance(row, dict) for row in data['servers']):
                raise ValueError('Invalid data structure')
            return data['servers'], dns
        if isinstance(data, list) and all(isinstance(row, dict) for row in data):
            return data, {}
        raise ValueError("Invalid data structure")

    def _versions(self):
        # В запросе baseline не меняется при вспомогательных чтениях DNS/карточек.
        if has_request_context():
            if not hasattr(g, '_vault_versions'):
                g._vault_versions = {}
            return g._vault_versions
        if not hasattr(self._observations, 'versions'):
            self._observations.versions = {}
        return self._observations.versions

    def read_payload(self, file_path: str, fernet: Optional[Fernet] = None):
        path = canonical(file_path)
        with open(path, 'rb') as stream:
            raw = stream.read()
        if not raw:
            raise VaultError(_('Пустой или повреждённый файл хранилища. Запись запрещена.'))
        servers, dns = self.split_payload(json.loads((fernet or self.fernet).decrypt(raw).decode('utf-8')))
        rev = revision(raw)
        versions = self._versions()
        if has_request_context():
            versions.setdefault(path, rev)
        else:
            versions[path] = rev
        return ServersSnapshot(servers, path, rev), DnsSnapshot(dns, path, rev)

    def load_dns(self, config: Dict[str, Any]) -> Dict[str, Any]:
        path = self.get_active_data_path(config)
        if not path:
            return {}
        return self.read_payload(path)[1]

    def save_dns(self, dns: Dict[str, Any], file_path: str) -> None:
        # Не делаем новое публичное чтение: оно скрыло бы старую revision DNS.
        self._save(None, file_path, dns)

    @staticmethod
    def _strip_runtime_secrets(servers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Убирает plaintext *_decrypted поля перед записью в файл."""
        cleaned = copy.deepcopy(servers)
        for server in cleaned:
            for section in ('ssh_credentials', 'panel_credentials', 'hoster_credentials'):
                creds = server.get(section)
                if not isinstance(creds, dict):
                    continue
                for key in list(creds.keys()):
                    if key.endswith('_decrypted'):
                        creds.pop(key, None)
        return cleaned
    
    def save_servers(self, servers: List[Dict[str, Any]], file_path: str,
                     dns: Optional[Dict[str, Any]] = None) -> None:
        self._save(servers, file_path, dns)

    def _save(self, servers, file_path, dns):
        path = canonical(file_path)
        versions = self._versions()
        snapshot = dns if isinstance(dns, DnsSnapshot) else servers
        expected = (snapshot.vault_revision if isinstance(snapshot, (ServersSnapshot, DnsSnapshot))
                    and snapshot.vault_path == path else versions.get(path))
        with file_lock(path):
            raw = Path(path).read_bytes() if os.path.exists(path) else None
            actual = revision(raw)
            # Проверяем целостность ДО записи. Неверный ключ не превращается в пустой DNS.
            if raw is not None:
                try:
                    old_servers, old_dns = self.split_payload(json.loads(self.fernet.decrypt(raw).decode('utf-8')))
                except (InvalidToken, ValueError, TypeError) as exc:
                    raise VaultError(_('Хранилище не прочитано. Проверьте ключ или восстановите резервную копию. Запись запрещена.')) from exc
            else:
                old_servers, old_dns = [], {}
            if actual != expected:
                raise VaultConflict(_('Хранилище изменилось. Обновите страницу и повторите изменения.'))
            clean = self._strip_runtime_secrets(old_servers if servers is None else servers)
            dns = old_dns if dns is None else dns
            payload = {'servers': clean, 'dns': dns} if dns else clean
            self.split_payload(payload)
            encrypted = self.fernet.encrypt(json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8'))
            if raw is not None:
                atomic_write(path + '.backup.enc', raw)
            atomic_write(path, encrypted)
            versions[path] = revision(encrypted)

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
            data, dns = self.split_payload(json.loads(decrypted_data))
            
            result['success'] = True
            result['dns_domain_count'] = len(dns.get('domains') or [])
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
        # Servers store their address in ip_address; 'ip' is kept for old files
        def server_ip_of(server):
            return server.get('ip_address') or server.get('ip') or ''

        existing_ips = {server_ip_of(server) for server in current_servers if server_ip_of(server)}
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
            server_ip = server_ip_of(server)
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

    def update_user_config(self, new_settings: Dict[str, Any]) -> bool:
        """
        Безопасно обновляет config.json пользователя.

        Args:
            new_settings: Словарь с новыми настройками для добавления/обновления.

        Returns:
            True, если обновление прошло успешно.
        """
        import logging
        logger = logging.getLogger(__name__)

        config_path = os.path.join(self.app_data_dir, 'config.json')
        
        try:
            from .config_io import read_config, write_config
            config_data = read_config(config_path)
            config_data.update(new_settings)
            write_config(config_path, config_data)

            logger.info(f"User config updated at {config_path} with keys: {list(new_settings.keys())}")
            return True
        except Exception as e:
            logger.error(f"Failed to update user config at {config_path}: {e}")
            return False

