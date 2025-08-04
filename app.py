import json
import os
import datetime
import sys
from pathlib import Path
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, make_response, send_from_directory, jsonify, flash, session
from dotenv import load_dotenv
from cryptography.fernet import Fernet, InvalidToken
from werkzeug.utils import secure_filename
import requests
from urllib.parse import urlparse
import copy
import threading
import subprocess
import shutil
import webview
import signal
import socket

load_dotenv()

app = Flask(__name__)

# Функция для определения директории для хранения данных
def get_app_data_dir():
    """
    Возвращает директорию для хранения пользовательских данных приложения.
    Учитывает различие между режимом разработки и запакованным приложением.
    """
    # Определяем, запущено ли приложение как пакет
    is_frozen = getattr(sys, 'frozen', False)
    
    # Имя директории приложения
    app_name = "VPNServerManager"
    
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
                os.environ.get('APPDATA', os.path.expanduser("~")),
                app_name
            )
        else:  # Linux и другие системы
            # ~/.local/share/VPNServerManager
            app_data_dir = os.path.join(
                os.path.expanduser("~"),
                ".local", "share",
                app_name
            )
    else:
        # В режиме разработки используем локальные пути
        app_data_dir = os.path.join(os.getcwd())
    
    # Создаем директории для данных и загрузок
    os.makedirs(os.path.join(app_data_dir, "data"), exist_ok=True)
    os.makedirs(os.path.join(app_data_dir, "uploads"), exist_ok=True)
    
    return app_data_dir

# --- НОВАЯ ЛОГИКА ИНИЦИАЛИЗАЦИИ КОНФИГА ---
APP_DATA_DIR = get_app_data_dir()
is_frozen = getattr(sys, 'frozen', False)

# Путь к конфигу в директории данных пользователя
user_config_path = Path(APP_DATA_DIR) / 'config.json'

def load_config_from_path(path):
    """Загружает JSON конфиг из указанного пути."""
    if not path.exists():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

# Шаг 1: Загрузить "эталонный" конфиг из бандла (если применимо)
bundle_config = None
if is_frozen:
    try:
        # sys._MEIPASS - это специальный путь, который PyInstaller создает в собранном приложении
        bundle_config_path = Path(sys._MEIPASS) / 'config.json'
        bundle_config = load_config_from_path(bundle_config_path)
    except Exception as e:
        print(f"Не удалось найти или загрузить эталонный конфиг: {e}")

# Шаг 2: Загрузить пользовательский конфиг
user_config = load_config_from_path(user_config_path)

# Шаг 3: Определить, какой конфиг использовать и нужно ли обновление
final_config = {}
if user_config is None and bundle_config is not None:
    # Случай 1: У пользователя нет конфига, копируем из бандла
    print(f"Пользовательский конфиг не найден. Копирование из {bundle_config_path}")
    try:
        shutil.copy(bundle_config_path, user_config_path)
        final_config = bundle_config
    except Exception as e:
        print(f"Ошибка копирования конфига: {e}")
        final_config = {} # Используем пустой, чтобы избежать сбоя
elif bundle_config is not None and user_config is not None:
    # Случай 2: Оба конфига есть. Сравниваем и обновляем.
    bundle_version = bundle_config.get('app_info', {}).get('version', '0.0.0')
    user_version = user_config.get('app_info', {}).get('version', '0.0.0')

    # Простое сравнение версий (можно заменить на более сложное, если нужно)
    if bundle_version > user_version:
        print(f"Найдена новая версия ({bundle_version} > {user_version}). Обновление конфига.")
        # Обновляем информацию о приложении, сохраняя остальные настройки пользователя
        user_config['app_info'] = bundle_config['app_info']
        final_config = user_config
        # Сохраняем обновленный конфиг
        try:
            with open(user_config_path, 'w', encoding='utf-8') as f:
                json.dump(user_config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Ошибка сохранения обновленного конфига: {e}")
    else:
        # Версия не новее, используем конфиг пользователя как есть
        final_config = user_config
else:
    # Случай 3: Используем конфиг пользователя (или пустой, если его нет и нет бандла)
    final_config = user_config if user_config is not None else {}
    if not is_frozen and not user_config_path.exists():
        print(f"ВНИМАНИЕ: {user_config_path} не найден в режиме разработки. Будет создан пустой.")
        # Создаем пустой файл, чтобы избежать ошибок при последующих сохранениях
        with open(user_config_path, 'w', encoding='utf-8') as f:
            json.dump({}, f)

# Загрузка основной конфигурации в Flask
app.config.update(final_config)

# Убедимся, что PIN-настройки загружены в app.config
if 'secret_pin' in final_config:
    app.config['secret_pin'] = final_config['secret_pin']


# Если `app_info` все еще отсутствует (например, при самом первом запуске в dev), добавляем заглушку
if 'app_info' not in app.config:
    app.config['app_info'] = {
        "version": "N/A",
        "last_updated": "N/A",
        "developer": "N/A"
    }

# Добавим фильтр для Jinja2
def format_datetime_filter(iso_str):
    """Jinja фильтр для форматирования ISO-строки с датой и временем."""
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.datetime.fromisoformat(iso_str)
        return dt.strftime('%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        return iso_str

app.jinja_env.filters['format_datetime'] = format_datetime_filter

@app.context_processor
def inject_app_info():
    """Инжектирует информацию о приложении во все шаблоны."""
    return {'app_info': app.config.get('app_info', {})}

# Ключ для flash-сообщений
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "a-default-secret-key-for-flash")

# Импортируем PIN-аутентификацию после настройки приложения
from pin_auth import pin_auth

# Устанавливаем пути относительно директории данных приложения
app.config['UPLOAD_FOLDER'] = os.path.join(APP_DATA_DIR, 'uploads')
# Расширяем разрешенные расширения для зашифрованных данных
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'rtf', 'md', 'pdf', 'png', 'jpg', 'jpeg', 'enc'}

# Убедимся, что папки для загрузок и данных существуют
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(APP_DATA_DIR, 'data'), exist_ok=True)

@app.context_processor
def inject_request():
    return {'request': request}

@app.context_processor
def inject_service_urls():
    # Инжектируем URL-адреса сервисов и путь к активному файлу данных
    return {
        'service_urls': app.config.get('service_urls', {}),
        'active_data_file': get_active_data_path()  # Используем полный абсолютный путь
    }

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# --- NEW, ROBUST LOGIC FOR SECRET_KEY ---
SECRET_KEY = None
is_frozen = getattr(sys, 'frozen', False)

if is_frozen:
    # Для упакованного приложения ищем .env в пользовательской директории И в bundle
    try:
        # Сначала пробуем пользовательскую директорию
        user_dotenv_path = Path(APP_DATA_DIR) / '.env'
        if user_dotenv_path.exists():
            load_dotenv(dotenv_path=user_dotenv_path)
            SECRET_KEY = os.getenv("SECRET_KEY")
        
        # Если не найден в пользовательской директории, пробуем bundle (для совместимости)
        if not SECRET_KEY:
            base_path = Path(sys.executable).parent.parent / 'Resources'
            bundle_dotenv_path = base_path / '.env'
            if bundle_dotenv_path.exists():
                load_dotenv(dotenv_path=bundle_dotenv_path)
                SECRET_KEY = os.getenv("SECRET_KEY")
    except Exception:
        SECRET_KEY = None
else:
    # Для разработки, ищем .env в корне проекта
    load_dotenv()
    SECRET_KEY = os.getenv("SECRET_KEY")


if not SECRET_KEY:
    # Этот код выполнится, если .env не найден или пуст.
    try:
        # Просто вызываем ошибку, без GUI
        raise ValueError("SECRET_KEY не найден. Проблема с путем или сборкой.")
    except Exception as e:
        print(f"Ошибка отображения messagebox: {e}")
    
    raise ValueError("Не найден SECRET_KEY в .env файле. Сгенерируйте его.")

fernet = Fernet(SECRET_KEY.encode())

def encrypt_data(data):
    if not data:
        return ""
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data):
    """
    Расшифровывает данные, зашифрованные с помощью Fernet.
    Автоматически определяет формат данных и обрабатывает их соответственно.
    """
    # Проверяем на пустые данные в начале
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
            return fernet.decrypt(encrypted_data.encode()).decode()
        except Exception:
            # Если расшифровка не удалась, возвращаем пустую строку
            return ""
    
    # Если данные выглядят как обычный текст (не содержат специальных символов), возвращаем как есть
    # Зашифрованные Fernet данные всегда содержат специальные символы и начинаются с определенных префиксов
    try:
        import base64
        # Пытаемся декодировать как base64 для проверки формата
        decoded = base64.b64decode(encrypted_data)
        
        # Проверяем, начинаются ли декодированные данные с байтов, характерных для Fernet
        # Fernet использует специальную структуру: версия (0x80) + timestamp (8 bytes) + IV (16 bytes) + data + HMAC (32 bytes)
        if len(decoded) >= 57 and decoded[0] == 0x80:  # Минимальная длина Fernet token и версия
            # Это похоже на зашифрованные данные Fernet, пытаемся расшифровать
            try:
                return fernet.decrypt(encrypted_data.encode()).decode()
            except Exception:
                # Если расшифровка не удалась, возвращаем пустую строку
                return ""
        else:
            # Это не Fernet данные, возможно просто base64 строка или обычный текст
            return encrypted_data
    except Exception:
        # Если декодирование base64 не удалось или это не Fernet формат
        # Проверяем, может это простой текст
        if all(ord(c) < 128 and c.isprintable() for c in encrypted_data):
            # Это обычный ASCII текст
            return encrypted_data
        else:
            # Последняя попытка расшифровки
            try:
                return fernet.decrypt(encrypted_data.encode()).decode()
            except Exception:
                # Если ничего не помогло, возвращаем пустую строку вместо зашифрованных данных
                return ""

def save_app_config():
    """Сохраняет текущую JSON-совместимую конфигурацию в файл."""
    # Сначала читаем текущий файл, чтобы не потерять ключи, которых нет в app.config
    config_path = os.path.join(APP_DATA_DIR, 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_to_save = json.load(f)
            if not isinstance(config_to_save, dict):
                config_to_save = {}
    except (FileNotFoundError, json.JSONDecodeError):
        config_to_save = {}

    # Обновляем ключи из app.config, которые должны быть в JSON
    for key in ['version', 'developer', 'service_urls', 'app_info']:
        if key in app.config:
            config_to_save[key] = app.config[key]
    
    # Сохраняем PIN-настройки, если они есть
    if 'secret_pin' in app.config:
        config_to_save['secret_pin'] = app.config['secret_pin']
            
    # Особо обрабатываем active_data_file
    if app.config.get('active_data_file'):
        config_to_save['active_data_file'] = app.config['active_data_file']
    else:
        # Удаляем ключ, если он None или пустая строка
        config_to_save.pop('active_data_file', None)
        
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_to_save, f, ensure_ascii=False, indent=2)

def get_active_data_path():
    """Возвращает полный путь к активному файлу данных из конфигурации."""
    path = app.config.get('active_data_file')
    if path:
        # Если путь относительный, сделать его абсолютным относительно APP_DATA_DIR
        if not os.path.isabs(path):
            return os.path.join(APP_DATA_DIR, path)
        return path
    return None

def get_export_dir():
    """Возвращает безопасную директорию для экспорта файлов."""
    # Используем папку Downloads пользователя - стандартное место для загрузок
    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.exists(downloads_dir) and os.access(downloads_dir, os.W_OK):
        return downloads_dir
    
    # Если Downloads недоступна, используем APP_DATA_DIR
    return APP_DATA_DIR


def get_day_with_suffix(d):
    return str(d) + ("th" if 4 <= d <= 20 or 24 <= d <= 30 else {1: "st", 2: "nd", 3: "rd"}.get(d % 10, "th"))

def analyze_hosting(ip_info):
    if not ip_info:
        return {"text": "Неизвестно", "quality": "secondary"}
    
    # Расширенный черный список ключевых слов для хостингов, VPN и дата-центров
    bad_keywords = [
        # Общие термины
        'hosting', 'vpn', 'proxy', 'datacenter', 'vps', 'server', 'cloud', 'cdn', 'dedicated',
        
        # Крупные хостинг-провайдеры и облака
        'hetzner', 'ovh', 'digitalocean', 'linode', 'vultr', 'contabo', 'leaseweb', 'scaleway',
        'amazon', 'aws', 'google', 'gcp', 'microsoft', 'azure', 'oracle', 'ionos', 'upcloud',
        'godaddy', 'bluehost', 'hostgator', 'dreamhost', 'liquidweb', 'choopa', 'frantech',
        'datacamp', # Добавлено для вашего случая
        
        # Названия известных VPN-сервисов
        'nord', 'expressvpn', 'cyberghost', 'private internet access', 'pia', 'surfshark',
        'vyprvpn', 'tunnelbear', 'proton'
    ]
    
    org = ip_info.get('org', '').lower()
    for keyword in bad_keywords:
        if keyword in org:
            return {"text": "Хостинг", "quality": "danger"}

    # Исправлена проверка с .get('hosting') на .get('host')
    if ip_info.get('hosting', {}).get('host'):
         return {"text": "Хостинг", "quality": "danger"}

    return {"text": "ISP/Residential", "quality": "success"}

def load_servers():
    """Загружает и расшифровывает серверы из активного зашифрованного файла."""
    active_file = get_active_data_path()
    if not active_file:
        print("Активный файл данных не найден")
        return []
    
    if not os.path.exists(active_file):
        print(f"Файл данных не существует: {active_file}")
        return []

    try:
        with open(active_file, 'rb') as f:
            encrypted_data = f.read()

        if not encrypted_data:
            print("Файл данных пуст")
            return []

        decrypted_data = fernet.decrypt(encrypted_data)
        servers = json.loads(decrypted_data.decode('utf-8'))
        
        today = date.today()
        # Расшифровываем конфиденциальные данные для отображения
        for server in servers:
            # Для обратной совместимости добавляем недостающие ключи
            if 'status' not in server:
                server['status'] = 'Active' # Статус по умолчанию
            if 'payment_info' not in server:
                server['payment_info'] = {}
            if 'payment_period' not in server['payment_info']:
                server['payment_info']['payment_period'] = ''
            if 'panel_credentials' not in server:
                server['panel_credentials'] = {}
            if 'hoster_credentials' not in server:
                server['hoster_credentials'] = {}
            if 'login_method' not in server.get('hoster_credentials', {}):
                server['hoster_credentials']['login_method'] = 'password'
            if 'geolocation' not in server:
                server['geolocation'] = {}
            if 'checks' not in server:
                server['checks'] = {"dns_ok": False, "streaming_ok": False}

            if "ssh_credentials" in server:
                if 'root_password' not in server['ssh_credentials']:
                    server['ssh_credentials']['root_password'] = ''
                if 'root_login_allowed' not in server['ssh_credentials']:
                    server['ssh_credentials']['root_login_allowed'] = False
                server["ssh_credentials"]["password_decrypted"] = decrypt_data(server["ssh_credentials"].get("password", ""))
                server["ssh_credentials"]["root_password_decrypted"] = decrypt_data(server["ssh_credentials"].get("root_password", ""))
            
            # Автоматическое обновление статуса на основе даты платежа
            due_date_str = server.get('payment_info', {}).get('next_due_date')
            if server.get('status') == 'Active' and due_date_str:
                try:
                    due_date = datetime.datetime.strptime(due_date_str, '%Y-%m-%d').date()
                    if due_date < today:
                        delta = today - due_date
                        if delta.days > 5:
                            server['status'] = 'Удален'
                        else:
                            server['status'] = 'Приостановлен'
                except (ValueError, TypeError):
                    pass  # Игнорируем неверный формат даты

            # Анализ хостинга
            server['hosting_analysis'] = analyze_hosting(server.get('geolocation'))

            # Форматируем дату
            due_date_str = server.get('payment_info', {}).get('next_due_date')
            if due_date_str:
                try:
                    date_obj = datetime.datetime.strptime(due_date_str, '%Y-%m-%d').date()
                    day_with_suffix = get_day_with_suffix(date_obj.day)
                    server['payment_info']['formatted_date'] = date_obj.strftime(f'%B {day_with_suffix}, %Y')
                except (ValueError, TypeError):
                    server['payment_info']['formatted_date'] = due_date_str
            else:
                server['payment_info']['formatted_date'] = 'N/A'


            if "ssh_credentials" in server and "password" in server["ssh_credentials"]:
                pass # Логика перенесена выше для согласованности
            
            # Расшифровываем данные панели управления
            if "panel_credentials" in server:
                server["panel_credentials"]["user_decrypted"] = decrypt_data(server["panel_credentials"].get("user", ""))
                server["panel_credentials"]["password_decrypted"] = decrypt_data(server["panel_credentials"].get("password", ""))

            # Расшифровываем данные кабинета хостера
            if "hoster_credentials" in server:
                server["hoster_credentials"]["user_decrypted"] = decrypt_data(server["hoster_credentials"].get("user", ""))
                server["hoster_credentials"]["password_decrypted"] = decrypt_data(server["hoster_credentials"].get("password", ""))

            if 'receipts' in server.get('payment_info', {}):
                # Сортировка чеков по дате загрузки (от новых к старым)
                server['payment_info']['receipts'].sort(key=lambda r: r.get('upload_date', ''), reverse=True)

        print(f"Успешно загружено {len(servers)} серверов")
        return servers
    except FileNotFoundError:
        print(f"Файл данных не найден: {active_file}")
        return []
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON: {e}")
        flash('Ошибка чтения файла данных. Файл может быть поврежден.', 'danger')
        return []
    except (InvalidToken, Exception) as e:
        # Если ключ неверный или файл поврежден
        print(f"Ошибка расшифровки данных: {e}")
        flash('Не удалось расшифровать файл данных. Проверьте ваш SECRET_KEY или целостность файла.', 'danger')
        return []

def save_servers(servers):
    """Шифрует и сохраняет полный список серверов в активный файл."""
    active_file = get_active_data_path()
    if not active_file:
        flash('Ошибка: не указан активный файл данных. Сохранение невозможно.', 'danger')
        return

    # Создаем копию для безопасного сохранения, удаляя временные поля
    servers_to_save = copy.deepcopy(servers)
    for server in servers_to_save:
        # Удаляем все временные расшифрованные ключи
        if 'ssh_credentials' in server:
            server['ssh_credentials'].pop('password_decrypted', None)
            server['ssh_credentials'].pop('root_password_decrypted', None)
        if 'panel_credentials' in server:
            server['panel_credentials'].pop('user_decrypted', None)
            server['panel_credentials'].pop('password_decrypted', None)
        if 'hoster_credentials' in server:
            server['hoster_credentials'].pop('user_decrypted', None)
            server['hoster_credentials'].pop('password_decrypted', None)
        
        # Удаляем другие временные поля, созданные для UI
        server.pop('hosting_analysis', None)
        server.pop('os_icon', None)
        server.pop('masked_panel_url', None)
        if 'payment_info' in server:
            server['payment_info'].pop('formatted_date', None)

    try:
        json_string = json.dumps(servers_to_save, ensure_ascii=False, indent=2)
        encrypted_data = fernet.encrypt(json_string.encode('utf-8'))
        
        with open(active_file, 'wb') as f:
            f.write(encrypted_data)
    except Exception as e:
        flash(f'Произошла ошибка при сохранении файла: {e}', 'danger')


def load_hints():
    try:
        hints_path = os.path.join(APP_DATA_DIR, 'data', 'hints.json')
        with open(hints_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_hints(hints):
    hints_path = os.path.join(APP_DATA_DIR, 'data', 'hints.json')
    with open(hints_path, 'w', encoding='utf-8') as f:
        json.dump(hints, f, ensure_ascii=False, indent=2)

def migrate_data_if_needed():
    """
    Выполняет однократную миграцию из старого формата `servers.json`
    в новый зашифрованный `servers.json.enc`.
    Также мигрирует из локальных файлов в директорию данных приложения.
    """
    # Путь к файлам в старой директории проекта
    old_json_path = 'data/servers.json'
    old_enc_path = 'data/servers.json.enc'
    
    # Путь к файлу в новой директории данных
    new_enc_path = os.path.join(APP_DATA_DIR, 'data', 'servers.json.enc')
    
    # Сначала проверяем, нужно ли мигрировать из старого json в новый enc
    if os.path.exists(old_json_path) and not os.path.exists(old_enc_path) and not os.path.exists(new_enc_path):
        print("Обнаружен старый файл данных. Выполняется миграция...")
        try:
            # Загружаем старые данные
            with open(old_json_path, 'r', encoding='utf-8') as f:
                servers = json.load(f)
            
            # Сохраняем их в новом зашифрованном формате в новой директории
            json_string = json.dumps(servers, ensure_ascii=False, indent=2)
            encrypted_data = fernet.encrypt(json_string.encode('utf-8'))
            with open(new_enc_path, 'wb') as f:
                f.write(encrypted_data)

            # Обновляем config.json, чтобы использовать новый файл по умолчанию
            app.config['active_data_file'] = os.path.join('data', 'servers.json.enc')
            save_app_config()
            
            # Переименовываем старый файл, чтобы избежать повторной миграции
            os.rename(old_json_path, old_json_path + '.bak')
            print(f"Миграция успешно завершена. Данные сохранены в {new_enc_path}.")
            print(f"Старый файл переименован в {old_json_path}.bak.")
        except Exception as e:
            print(f"Ошибка миграции данных: {e}")
    
    # Затем проверяем, нужно ли мигрировать из старого зашифрованного формата в новую директорию
    elif os.path.exists(old_enc_path) and not os.path.exists(new_enc_path):
        print("Выполняется миграция шифрованного файла в новую директорию...")
        try:
            # Копируем файл в новую директорию
            os.makedirs(os.path.dirname(new_enc_path), exist_ok=True)
            with open(old_enc_path, 'rb') as src, open(new_enc_path, 'wb') as dst:
                dst.write(src.read())
            
            # Обновляем config.json, чтобы использовать новый файл по умолчанию
            app.config['active_data_file'] = os.path.join('data', 'servers.json.enc')
            save_app_config()
            
            print(f"Миграция файла в новую директорию завершена успешно.")
        except Exception as e:
            print(f"Ошибка миграции файла: {e}")
    
    # Если файл данных не прикреплен или не существует, создаем его
    active_file = get_active_data_path()
    if not active_file or not os.path.exists(active_file):
        print("Активный файл данных не прикреплен или не существует. Создание файла по умолчанию...")
        default_path = os.path.join('data', 'servers.json.enc')
        full_path = os.path.join(APP_DATA_DIR, default_path)
        
        # Создаем пустой файл, если он не существует
        if not os.path.exists(full_path):
            try:
                json_string = json.dumps([], ensure_ascii=False, indent=2)
                encrypted_data = fernet.encrypt(json_string.encode('utf-8'))
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'wb') as f:
                    f.write(encrypted_data)
                    
                # Обновляем config.json, чтобы использовать новый файл по умолчанию
                app.config['active_data_file'] = default_path
                save_app_config()
                
                print(f"Создан новый файл данных: {full_path}")
            except Exception as e:
                print(f"Ошибка создания файла данных: {e}")

# Выполняем проверку и миграцию при старте приложения
migrate_data_if_needed()


@app.after_request
def add_security_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response



@app.route('/pin/login_ajax', methods=['POST'])
def pin_login_ajax():
    """AJAX обработчик входа по PIN."""
    try:
        if pin_auth.is_pin_login_blocked():
            remaining = pin_auth.get_pin_block_remaining()
            return jsonify({
                'success': False, 
                'message': f'Вход заблокирован на {remaining} секунд',
                'blocked': True,
                'remaining_seconds': remaining
            }), 429
        
        pin = request.form.get('pin', '').strip()
        
        if not pin:
            return jsonify({'success': False, 'message': 'Введите PIN-код'}), 400
        
        success, message = pin_auth.authenticate_pin(pin)
        
        if success:
            return jsonify({'success': True, 'message': 'Аутентификация успешна'})
        else:
            if pin_auth.is_pin_login_blocked():
                remaining = pin_auth.get_pin_block_remaining()
                return jsonify({
                    'success': False, 
                    'message': message,
                    'blocked': True,
                    'remaining_seconds': remaining
                }), 429
            else:
                return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка аутентификации: {e}'}), 500

@app.route('/pin/check_archive', methods=['POST'])
def check_archive_for_pin():
    """Проверяет архив на наличие PIN-кода."""
    try:
        uploaded_file = request.files.get('archive_file')
        if not uploaded_file or not uploaded_file.filename.endswith('.zip'):
            return jsonify({'success': False, 'message': 'Выберите ZIP архив'})
        
        # Создаем временный файл
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
            uploaded_file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            import zipfile
            with zipfile.ZipFile(temp_file_path, 'r') as zipf:
                # Ищем файл PIN.txt в архиве
                pin_file = None
                for file_info in zipf.filelist:
                    if file_info.filename == 'PIN.txt':
                        pin_file = file_info
                        break
                
                if pin_file:
                    # Читаем PIN из архива
                    pin_content = zipf.read('PIN.txt').decode('utf-8')
                    pin_line = pin_content.strip()
                    if pin_line.startswith('PIN='):
                        pin = pin_line[4:]  # Убираем "PIN="
                        return jsonify({
                            'success': True, 
                            'pin': pin,
                            'message': f'Найден PIN-код: {pin}'
                        })
                    else:
                        return jsonify({'success': False, 'message': 'Неверный формат PIN в архиве'})
                else:
                    return jsonify({'success': False, 'message': 'PIN-код не найден в архиве'})
                    
        except zipfile.BadZipFile:
            return jsonify({'success': False, 'message': 'Неверный формат ZIP архива'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Ошибка чтения архива: {str(e)}'})
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка обработки файла: {str(e)}'})

@app.route('/pin/import_archive', methods=['POST'])
def import_archive_with_pin():
    """Импортирует данные из архива и устанавливает PIN."""
    try:
        uploaded_file = request.files.get('archive_file')
        if not uploaded_file or not uploaded_file.filename.endswith('.zip'):
            return jsonify({'success': False, 'message': 'Выберите ZIP архив'})
        
        # Создаем временный файл
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
            uploaded_file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            import zipfile
            with zipfile.ZipFile(temp_file_path, 'r') as zipf:
                # Проверяем наличие необходимых файлов
                required_files = ['PIN.txt', 'SECRET_KEY.env']
                missing_files = []
                
                for required_file in required_files:
                    if required_file not in [f.filename for f in zipf.filelist]:
                        missing_files.append(required_file)
                
                if missing_files:
                    return jsonify({
                        'success': False, 
                        'message': f'В архиве отсутствуют файлы: {", ".join(missing_files)}'
                    })
                
                # Проверяем наличие данных серверов (может быть в разных форматах)
                servers_data_file = None
                possible_server_files = ['servers.json.enc', 'servers.json', 'data.json.enc', 'data.json']
                
                # Сначала ищем точные совпадения
                for file_info in zipf.filelist:
                    if file_info.filename in possible_server_files:
                        servers_data_file = file_info.filename
                        break
                
                # Если точных совпадений нет, ищем файлы с .enc расширением и содержащие "servers"
                if not servers_data_file:
                    for file_info in zipf.filelist:
                        if file_info.filename.endswith('.enc') and 'servers' in file_info.filename.lower():
                            servers_data_file = file_info.filename
                            break
                
                # Если и это не найдено, ищем любые .enc файлы
                if not servers_data_file:
                    for file_info in zipf.filelist:
                        if file_info.filename.endswith('.enc'):
                            servers_data_file = file_info.filename
                            break
                
                if not servers_data_file:
                    return jsonify({
                        'success': False, 
                        'message': 'В архиве не найдены данные серверов'
                    })
                
                # Читаем PIN
                pin_content = zipf.read('PIN.txt').decode('utf-8')
                pin_line = pin_content.strip()
                if not pin_line.startswith('PIN='):
                    return jsonify({'success': False, 'message': 'Неверный формат PIN в архиве'})
                pin = pin_line[4:]  # Убираем "PIN="
                
                # Читаем SECRET_KEY
                secret_key_content = zipf.read('SECRET_KEY.env').decode('utf-8')
                secret_key_line = None
                for line in secret_key_content.split('\n'):
                    if line.startswith('SECRET_KEY='):
                        secret_key_line = line
                        break
                
                if not secret_key_line:
                    return jsonify({'success': False, 'message': 'SECRET_KEY не найден в архиве'})
                
                secret_key = secret_key_line[11:]  # Убираем "SECRET_KEY="
                
                # Читаем данные серверов
                servers_data = zipf.read(servers_data_file)
                
                # Определяем, зашифрованы ли данные
                is_encrypted = servers_data_file.endswith('.enc')
                
                # Устанавливаем новый SECRET_KEY
                app.config['SECRET_KEY'] = secret_key
                global fernet
                fernet = Fernet(secret_key.encode())
                
                # Устанавливаем новый PIN
                success, message = pin_auth.change_pin_without_old(pin)
                if not success:
                    return jsonify({'success': False, 'message': f'Ошибка установки PIN: {message}'})
                
                # Сохраняем данные серверов
                active_file = get_active_data_path()
                if active_file:
                    if is_encrypted:
                        # Если данные зашифрованы, сохраняем как есть
                        with open(active_file, 'wb') as f:
                            f.write(servers_data)
                    else:
                        # Если данные не зашифрованы, шифруем их перед сохранением
                        try:
                            # Пытаемся расшифровать как JSON
                            json_data = servers_data.decode('utf-8')
                            # Шифруем данные
                            encrypted_data = fernet.encrypt(json_data.encode('utf-8'))
                            with open(active_file, 'wb') as f:
                                f.write(encrypted_data)
                        except Exception as e:
                            return jsonify({
                                'success': False, 
                                'message': f'Ошибка обработки данных серверов: {str(e)}'
                            })
                
                # Сохраняем обновленную конфигурацию
                save_app_config()
                
                # Аутентифицируем пользователя
                session['pin_authenticated'] = True
                session['pin_login_used'] = True
                
                return jsonify({
                    'success': True, 
                    'message': 'Данные успешно импортированы из архива'
                })
                    
        except zipfile.BadZipFile:
            return jsonify({'success': False, 'message': 'Неверный формат ZIP архива'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Ошибка импорта: {str(e)}'})
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка обработки файла: {str(e)}'})

@app.route('/pin/first_time_setup', methods=['POST'])
def first_time_setup():
    """Настройка для первого запуска - создание нового PIN и сброс данных."""
    try:
        new_pin = request.form.get('new_pin', '').strip()
        
        if not new_pin or len(new_pin) < 4:
            return jsonify({'success': False, 'message': 'PIN должен содержать минимум 4 символа'})
        
        # Создаем новый PIN без проверки старого
        success, message = pin_auth.change_pin_without_old(new_pin)
        
        if success:
            # Сохраняем обновленную конфигурацию
            save_app_config()
            # Сбрасываем данные - создаем пустой файл данных
            active_file = get_active_data_path()
            if active_file:
                # Создаем пустой зашифрованный файл
                empty_data = json.dumps([], ensure_ascii=False, indent=2)
                encrypted_data = fernet.encrypt(empty_data.encode('utf-8'))
                
                with open(active_file, 'wb') as f:
                    f.write(encrypted_data)
            
            # Аутентифицируем пользователя
            session['pin_authenticated'] = True
            session['pin_login_used'] = True
            
            return jsonify({'success': True, 'message': 'Настройка завершена успешно'})
        else:
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка настройки: {e}'}), 500

@app.route('/pin/logout', methods=['POST'])
def pin_logout():
    """Выход из системы по PIN."""
    session.pop('pin_authenticated', None)
    session.pop('pin_login_used', None)
    return jsonify({'success': True, 'message': 'Выход выполнен успешно'})

@app.route('/pin/change_ajax', methods=['POST'])
def change_pin_ajax():
    """AJAX обработчик смены PIN."""
    try:
        old_pin = request.form.get('old_pin', '').strip()
        new_pin1 = request.form.get('new_pin1', '').strip()
        new_pin2 = request.form.get('new_pin2', '').strip()
        
        # Проверяем, что новый PIN введен дважды одинаково
        if new_pin1 != new_pin2:
            return jsonify({'success': False, 'message': 'Новые PIN-коды не совпадают'})
        
        # Проверяем, что новый PIN не пустой
        if not new_pin1:
            return jsonify({'success': False, 'message': 'Новый PIN не может быть пустым'})
        
        # Проверяем минимальную длину
        if len(new_pin1) < 4:
            return jsonify({'success': False, 'message': 'PIN должен содержать минимум 4 символа'})
        
        # Пытаемся сменить PIN
        success, message = pin_auth.change_pin(old_pin, new_pin1)
        
        if success:
            # Сохраняем обновленную конфигурацию
            save_app_config()
        
        return jsonify({'success': success, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'}), 500

@app.route('/pin/check_auth', methods=['GET'])
def check_auth():
    """Проверка статуса аутентификации."""
    return jsonify({'authenticated': pin_auth.is_authenticated()})

@app.route('/pin/check_block', methods=['GET'])
def check_block():
    """Проверка статуса блокировки PIN."""
    blocked = pin_auth.is_pin_login_blocked()
    remaining_seconds = pin_auth.get_pin_block_remaining() if blocked else 0
    print(f"🔍 Проверка блокировки: заблокирован={blocked}, осталось_секунд={remaining_seconds}")
    return jsonify({
        'blocked': blocked,
        'remaining_seconds': remaining_seconds
    })

@app.route('/')
def index():
    # Проверяем аутентификацию по PIN
    if not pin_auth.is_authenticated():
        return render_template('index_locked.html')
    
    try:
        servers = load_servers()
    except Exception as e:
        print(f"Ошибка загрузки серверов: {e}")
        servers = []
        flash('Не удалось загрузить данные серверов. Проверьте подключение к интернету и целостность файла данных.', 'warning')
    
    def get_os_icon(os_name):
        os_lower = os_name.lower()
        if 'windows' in os_lower:
            return 'bi-windows'
        if 'ubuntu' in os_lower:
            return 'bi-box-seam'
        if 'debian' in os_lower:
            return 'bi-box'
        if 'centos' in os_lower:
            return 'bi-archive'
        if 'linux' in os_lower:
            return 'bi-server'
        return 'bi-question-circle'
    
    def mask_url_path(url_string):
        if not url_string or not url_string.strip():
            return ""
        try:
            parsed = urlparse(url_string)
            # Отображаем только схему и хост. Добавляем /... если есть путь или порт.
            display_url = f"{parsed.scheme}://{parsed.hostname}"
            has_path = parsed.path and parsed.path != '/'
            has_port = parsed.port is not None
            if has_path or has_port:
                display_url += "/..."
            else:
                return url_string # Возвращаем как есть, если нечего скрывать
            return display_url
        except Exception:
            return url_string 

    # Проверяем доступность интернета
    internet_available = True
    try:
        # Быстрая проверка интернета
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=3)
    except OSError:
        internet_available = False
        flash('Нет подключения к интернету. Некоторые функции могут быть недоступны.', 'info')

    for server in servers:
        server['os_icon'] = get_os_icon(server.get('os', ''))
        server['masked_panel_url'] = mask_url_path(server.get('panel_url', ''))
        
    return render_template('index.html', servers=servers, internet_available=internet_available)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/add', methods=['GET', 'POST'])
@pin_auth.require_auth
def add_server():
    # Если файл данных не прикреплен, создаем его по умолчанию "на лету"
    if not get_active_data_path():
        print("Активный файл данных не прикреплен. Создание файла по умолчанию...")
        default_path = os.path.join('data', 'servers.json.enc')
        full_path = os.path.join(APP_DATA_DIR, default_path)
        
        # Создаем пустой файл, только если он не существует, чтобы не затереть данные
        if not os.path.exists(full_path):
            try:
                json_string = json.dumps([], ensure_ascii=False, indent=2)
                encrypted_data = fernet.encrypt(json_string.encode('utf-8'))
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'wb') as f:
                    f.write(encrypted_data)
            except Exception as e:
                # В случае ошибки, сообщаем и прерываем, чтобы избежать проблем
                flash(f'Критическая ошибка: не удалось создать файл данных. {e}', 'danger')
                return redirect(url_for('index'))

        # Прикрепляем файл в конфигурации
        app.config['active_data_file'] = default_path
        save_app_config()
        flash('Создан новый файл для хранения серверов. Теперь можно добавить первый.', 'info')

    if request.method == 'POST':
        servers = load_servers()
        new_id = max([s['id'] for s in servers] + [0]) + 1

        new_server = {
            "id": new_id,
            "provider": request.form['provider'],
            "name": request.form['name'],
            "ip_address": request.form['ip_address'],
            "os": request.form['os'],
            "status": request.form.get('status', 'Active'),
            "card_color": request.form.get('card_color', '#ffc107'),
            "icon_filename": None,
            "geolocation": {},
            "checks": {
                "dns_ok": 'check_dns_ok' in request.form,
                "streaming_ok": 'check_streaming_ok' in request.form
            },
            "specs": {
                "cpu": request.form['cpu'],
                "ram": request.form['ram'],
                "disk": request.form['disk']
            },
            "payment_info": {
                "amount": float(request.form['amount']) if request.form['amount'] else 0,
                "currency": request.form['currency'],
                "next_due_date": request.form['next_due_date'],
                "payment_period": request.form.get('payment_period', ''),
                "receipts": []
            },
            "ssh_credentials": {
                "user": request.form.get('ssh_user', ''),
                "password": encrypt_data(request.form.get('ssh_password', '')),
                "port": int(request.form.get('ssh_port', 22)),
                "root_password": encrypt_data(request.form.get('ssh_root_password', '')),
                "root_login_allowed": 'root_login_allowed' in request.form
            },
            "panel_url": request.form.get('panel_url', ''),
            "panel_credentials": {
                "user": encrypt_data(request.form.get('panel_user', '')),
                "password": encrypt_data(request.form.get('panel_password', ''))
            },
            "hoster_url": request.form.get('hoster_url', ''),
            "hoster_credentials": {
                "login_method": request.form.get('hoster_login_method', 'password'),
                "user": encrypt_data(request.form.get('hoster_user', '')),
                "password": encrypt_data(request.form.get('hoster_password', ''))
            },
            "notes": request.form['notes'],
            "docker_info": request.form.get('docker_info', ''),
            "software_info": request.form.get('software_info', '')
        }
        
        # Получаем геолокацию
        try:
            # Используем URL из конфига с запасным вариантом
            ip_check_url = app.config.get('service_urls', {}).get('ip_check_api', 'https://ipinfo.io/{ip}/json').format(ip=new_server['ip_address'])
            response = requests.get(ip_check_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                new_server['geolocation'] = data # Сохраняем весь ответ
        except requests.exceptions.RequestException:
            pass # Игнорируем ошибку, если сервис недоступен
        
        # Обработка загрузки иконки
        if 'server_icon' in request.files:
            icon_file = request.files['server_icon']
            if icon_file and icon_file.filename != '' and allowed_file(icon_file.filename):
                original_filename = secure_filename(icon_file.filename)
                unique_filename = f"icon_{new_id}_{original_filename}"
                icon_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                new_server['icon_filename'] = unique_filename

        # Обработка загрузки файла чека
        if 'receipt' in request.files:
            file = request.files['receipt']
            description = request.form.get('receipt_description', 'Чек')
            if file and file.filename != '' and allowed_file(file.filename):
                original_filename = secure_filename(file.filename)
                # Создаем уникальное имя файла, чтобы избежать конфликтов
                unique_filename = f"{new_id}_{original_filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                new_server['payment_info']['receipts'].append({
                    'filename': unique_filename,
                    'original_name': original_filename,
                    'description': description,
                    'upload_date': datetime.datetime.now().isoformat()
                })

        servers.append(new_server)
        save_servers(servers)
        return redirect(url_for('index'))
    
    return render_template('add_server.html')

@app.route('/delete/<int:server_id>', methods=['POST'])
@pin_auth.require_auth
def delete_server(server_id):
    servers = load_servers()
    servers = [s for s in servers if s['id'] != server_id]
    save_servers(servers)
    return redirect(url_for('index'))

@app.route('/edit/<int:server_id>', methods=['GET', 'POST'])
@pin_auth.require_auth
def edit_server(server_id):
    servers = load_servers()
    server = next((s for s in servers if s['id'] == server_id), None)
    if not server:
        return "Сервер не найден!", 404

    if request.method == 'POST':
        # Обновляем данные сервера
        server['name'] = request.form['name']
        server['provider'] = request.form['provider']
        server['ip_address'] = request.form['ip_address']
        server['os'] = request.form['os']
        server['status'] = request.form.get('status', server.get('status'))
        server['card_color'] = request.form.get('card_color', server.get('card_color'))
        
        # Обновление SSH
        server['ssh_credentials']['user'] = request.form.get('ssh_user', server['ssh_credentials'].get('user'))
        server['ssh_credentials']['port'] = int(request.form.get('ssh_port', server['ssh_credentials'].get('port', 22)))
        if request.form.get('ssh_password'):
            server['ssh_credentials']['password'] = encrypt_data(request.form['ssh_password'])
            
        if request.form.get('ssh_root_password'):
            server['ssh_credentials']['root_password'] = encrypt_data(request.form.get('ssh_root_password'))
        
        server['ssh_credentials']['root_login_allowed'] = 'root_login_allowed' in request.form

        # Обновление specs
        if 'specs' not in server: server['specs'] = {}
        server['specs']['cpu'] = request.form.get('cpu', server['specs'].get('cpu'))
        server['specs']['ram'] = request.form.get('ram', server['specs'].get('ram'))
        server['specs']['disk'] = request.form.get('disk', server['specs'].get('disk'))

        # Обновление payment_info
        if 'payment_info' not in server: server['payment_info'] = {}
        server['payment_info']['amount'] = float(request.form.get('amount')) if request.form.get('amount') else server['payment_info'].get('amount')
        server['payment_info']['currency'] = request.form.get('currency', server['payment_info'].get('currency'))
        server['payment_info']['next_due_date'] = request.form.get('next_due_date', server['payment_info'].get('next_due_date'))
        server['payment_info']['payment_period'] = request.form.get('payment_period', server.get('payment_info', {}).get('payment_period'))

        # Обновление URL-ов
        server['panel_url'] = request.form.get('panel_url', server.get('panel_url'))
        server['hoster_url'] = request.form.get('hoster_url', server.get('hoster_url'))

        # Обновление данных панели
        if 'panel_credentials' not in server: server['panel_credentials'] = {}
        server['panel_credentials']['user'] = encrypt_data(request.form.get('panel_user')) if request.form.get('panel_user') else server['panel_credentials'].get('user', '')
        if request.form.get('panel_password'):
            server['panel_credentials']['password'] = encrypt_data(request.form.get('panel_password'))

        # Обновление данных хостера
        if 'hoster_credentials' not in server: server['hoster_credentials'] = {}
        server['hoster_credentials']['login_method'] = request.form.get('hoster_login_method', server.get('hoster_credentials', {}).get('login_method'))
        server['hoster_credentials']['user'] = encrypt_data(request.form.get('hoster_user')) if request.form.get('hoster_user') else server['hoster_credentials'].get('user', '')
        if request.form.get('hoster_password'):
            server['hoster_credentials']['password'] = encrypt_data(request.form.get('hoster_password'))

        # Обновление заметок
        server['notes'] = request.form.get('notes', server.get('notes'))
        server['docker_info'] = request.form.get('docker_info', server.get('docker_info'))
        server['software_info'] = request.form.get('software_info', server.get('software_info'))
        
        # Обработка загрузки иконки
        if 'server_icon' in request.files:
            icon_file = request.files['server_icon']
            if icon_file and icon_file.filename != '' and allowed_file(icon_file.filename):
                # Удаляем старую иконку, если она есть
                if server.get('icon_filename'):
                    old_icon_path = os.path.join(app.config['UPLOAD_FOLDER'], server['icon_filename'])
                    if os.path.exists(old_icon_path):
                        os.remove(old_icon_path)
                
                original_filename = secure_filename(icon_file.filename)
                unique_filename = f"icon_{server_id}_{original_filename}"
                icon_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                server['icon_filename'] = unique_filename
        
        # Обработка загрузки файла чека (для основной формы)
        if 'receipt' in request.files:
            file = request.files['receipt']
            description = request.form.get('receipt_description', 'Чек')
            if file and file.filename != '' and allowed_file(file.filename):
                original_filename = secure_filename(file.filename)
                timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                unique_filename = f"{server_id}_{timestamp}_{original_filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                
                if 'receipts' not in server['payment_info']:
                    server['payment_info']['receipts'] = []
                    
                server['payment_info']['receipts'].append({
                    'filename': unique_filename,
                    'original_name': original_filename,
                    'description': description,
                    'upload_date': datetime.datetime.now().isoformat()
                })

        # Обновление геолокации. Теперь обновляется при каждом сохранении.
        server['ip_address'] = request.form['ip_address']
        try:
            ip_check_url = app.config.get('service_urls', {}).get('ip_check_api', 'https://ipinfo.io/{ip}/json').format(ip=server['ip_address'])
            response = requests.get(ip_check_url, timeout=5)
            if response.status_code == 200:
                server['geolocation'] = response.json()
        except requests.exceptions.RequestException:
            if 'geolocation' not in server:
                 server['geolocation'] = {}
        
        server['status'] = request.form.get('status', server.get('status'))
        
        # Обновление чек-листа
        if 'checks' not in server: server['checks'] = {}
        server['checks']['dns_ok'] = 'check_dns_ok' in request.form
        server['checks']['streaming_ok'] = 'check_streaming_ok' in request.form

        save_servers(servers)
        return redirect(url_for('index'))

    hints = load_hints()
    # Группируем подсказки для удобного отображения
    grouped_hints = {}
    for hint in hints:
        if hint['group'] not in grouped_hints:
            grouped_hints[hint['group']] = []
        grouped_hints[hint['group']].append(hint)

    return render_template('edit_server.html', server=server, hints=grouped_hints)


@app.route('/server/<int:server_id>/receipts/add', methods=['POST'])
def add_receipt(server_id):
    """Добавляет чек к серверу через AJAX."""
    servers = load_servers()
    server = next((s for s in servers if s['id'] == server_id), None)
    if not server:
        return jsonify({"error": "Сервер не найден"}), 404

    if 'receipt_file' not in request.files:
        return jsonify({"error": "Файл чека отсутствует"}), 400
    
    file = request.files['receipt_file']
    description = request.form.get('description', 'Чек')

    if file and file.filename != '' and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        unique_filename = f"{server_id}_{timestamp}_{original_filename}"
        
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
        
        if 'payment_info' not in server: server['payment_info'] = {}
        if 'receipts' not in server['payment_info']: server['payment_info']['receipts'] = []
            
        new_receipt = {
            'filename': unique_filename,
            'original_name': original_filename,
            'description': description,
            'upload_date': datetime.datetime.now().isoformat()
        }
        server['payment_info']['receipts'].append(new_receipt)
        
        save_servers(servers)
        
        # Возвращаем добавленный чек с отформатированной датой для UI
        new_receipt['formatted_date'] = datetime.datetime.fromisoformat(new_receipt['upload_date']).strftime('%Y-%m-%d %H:%M')
        return jsonify(new_receipt)
    
    return jsonify({"error": "Недопустимый файл"}), 400

@app.route('/server/<int:server_id>/receipts/delete/<path:filename>', methods=['POST'])
def delete_receipt(server_id, filename):
    """Удаляет чек сервера через AJAX."""
    servers = load_servers()
    server = next((s for s in servers if s['id'] == server_id), None)
    if not server:
        return jsonify({"error": "Сервер не найден"}), 404

    receipts = server.get('payment_info', {}).get('receipts', [])
    receipt_to_delete = next((r for r in receipts if r.get('filename') == filename), None)
    
    if not receipt_to_delete:
        return jsonify({"error": "Чек не найден"}), 404

    # Удаляем файл с диска
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError as e:
        print(f"Ошибка удаления файла {filepath}: {e}") # Логгируем, но не останавливаем процесс

    # Удаляем запись из JSON
    server['payment_info']['receipts'].remove(receipt_to_delete)
    save_servers(servers)
    
    return jsonify({"success": True, "message": "Чек удален"})


@app.route('/manage_hints', methods=['GET'])
def manage_hints_page():
    hints = load_hints()
    return render_template('manage_hints.html', hints=hints)

@app.route('/hints/add', methods=['POST'])
def add_hint():
    hints = load_hints()
    new_id = max([h['id'] for h in hints] + [0]) + 1
    
    new_hint = {
        "id": new_id,
        "group": request.form['group'],
        "command": request.form['command']
    }
    hints.append(new_hint)
    save_hints(hints)
    return redirect(url_for('manage_hints_page'))

@app.route('/hints/delete/<int:hint_id>', methods=['POST'])
def delete_hint(hint_id):
    hints = load_hints()
    hints = [h for h in hints if h['id'] != hint_id]
    save_hints(hints)
    return redirect(url_for('manage_hints_page'))

@app.route('/about')
def about_page():
    app_info = app.config.get('app_info', {})
    return render_template('about.html', app_info=app_info)

@app.route('/help')
def help_page():
    return render_template('help.html')

@app.route('/cheatsheet')
def cheatsheet_page():
    return render_template('cheatsheet.html')

@app.route('/settings')
@pin_auth.require_auth
def settings_page():
    """Отображает страницу управления данными."""
    return render_template('settings.html')

@app.route('/data/export')
def export_data():
    """Отдает текущий активный файл данных для скачивания."""
    active_file = get_active_data_path()
    if not active_file or not os.path.exists(active_file):
        flash('Нет активного файла данных для экспорта.', 'warning')
        return redirect(url_for('settings_page'))
    
    # Для PyWebView создаем копию файла в папке Downloads для удобного доступа
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"servers_export_{timestamp}.enc"
        export_dir = get_export_dir()
        export_path = os.path.join(export_dir, export_filename)
        
        # Копируем файл в папку Downloads
        import shutil
        shutil.copy2(active_file, export_path)
        
        flash(f'✅ Файл данных экспортирован как: {export_filename} в папку Downloads', 'success')
        
        return send_from_directory(
                export_dir, 
            export_filename, 
        as_attachment=True
    )
    except Exception as e:
        flash(f'Ошибка при экспорте: {str(e)}', 'danger')
        return redirect(url_for('settings_page'))

@app.route('/data/export_key')
def export_key():
    """Экспортирует SECRET_KEY в виде .env файла для скачивания."""
    try:
        # Создаем .env файл в папке Downloads
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        key_filename = f"SECRET_KEY_{timestamp}.env"
        export_dir = get_export_dir()
        key_path = os.path.join(export_dir, key_filename)
        
        with open(key_path, 'w', encoding='utf-8') as f:
            f.write(f"SECRET_KEY={SECRET_KEY}\n")
            f.write(f"FLASK_SECRET_KEY=portable_app_key\n")
        
        flash(f'✅ Ключ шифрования экспортирован как: {key_filename} в папку Downloads', 'success')
        
        return send_from_directory(
            export_dir,
            key_filename,
            as_attachment=True
        )
    except Exception as e:
        flash(f'Ошибка при экспорте ключа: {str(e)}', 'danger')
        return redirect(url_for('settings_page'))

@app.route('/data/export_package')
def export_package():
    """Создает ZIP архив с данными, ключом и загруженными файлами."""
    try:
        import zipfile
        from datetime import datetime
        
        # Проверяем наличие активного файла данных
        active_file = get_active_data_path()
        if not active_file or not os.path.exists(active_file):
            flash('Нет активного файла данных для экспорта.', 'warning')
            return redirect(url_for('settings_page'))
        
        # Создаем ZIP файл в папке Downloads
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f'vpn_servers_backup_{timestamp}.zip'
        export_dir = get_export_dir()
        zip_path = os.path.join(export_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Добавляем файл данных сервера
            zipf.write(active_file, f"servers_{timestamp}.enc")
            
            # Создаем и добавляем файл с ключом
            env_content = f"SECRET_KEY={SECRET_KEY}\nFLASK_SECRET_KEY=portable_app_key\n"
            zipf.writestr("SECRET_KEY.env", env_content)
            
            # Добавляем файл с PIN-кодом
            current_pin = pin_auth.get_secret_pin()
            pin_content = f"PIN={current_pin}\n"
            zipf.writestr("PIN.txt", pin_content)
            
            # Добавляем загруженные файлы (если они есть)
            uploads_dir = os.path.join(get_app_data_dir(), "uploads")
            if os.path.exists(uploads_dir):
                for filename in os.listdir(uploads_dir):
                    file_path = os.path.join(uploads_dir, filename)
                    if os.path.isfile(file_path):
                        zipf.write(file_path, f"uploads/{filename}")
            
            # Добавляем README с инструкциями
            readme_content = f"""VPN Server Manager - Экспорт данных
===========================================

Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

Содержимое архива:
- servers_{timestamp}.enc - Зашифрованные данные серверов
- SECRET_KEY.env - Ключ шифрования (поместите в папку с приложением)
- PIN.txt - PIN-код для входа в приложение
- uploads/ - Загруженные файлы (счета, скриншоты и т.д.)

Инструкция по импорту:
1. Скопируйте SECRET_KEY.env в папку с новой установкой VPN Server Manager
2. Переименуйте SECRET_KEY.env в .env
3. Перезапустите приложение
4. В разделе "Настройки" -> "Управление данными" импортируйте файл servers_{timestamp}.enc
5. Скопируйте содержимое папки uploads/ в папку uploads/ новой установки
6. Запомните PIN-код из файла PIN.txt для входа в приложение

ВАЖНО: Храните этот архив в безопасном месте. Любой, кто имеет доступ к нему,
может расшифровать ваши данные о серверах!
"""
            zipf.writestr("README.txt", readme_content)
        
        flash(f'✅ Полный архив создан как: {zip_filename} в папке Downloads', 'success')
        
        # Отправляем ZIP файл
        return send_from_directory(
            export_dir,
            zip_filename,
            as_attachment=True
        )
        
    except Exception as e:
        flash(f'Ошибка при создании архива: {str(e)}', 'danger')
        return redirect(url_for('settings_page'))

@app.route('/data/import', methods=['POST'])
def import_data():
    global app_config
    try:
        uploaded_file = request.files['data_file']
        if uploaded_file and allowed_file(uploaded_file.filename) and uploaded_file.filename.endswith('.enc'):
            # Создаем уникальное имя файла с временной меткой
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"imported_{timestamp}_{secure_filename(uploaded_file.filename)}"
            
            # Получаем директорию для хранения данных
            app_data_dir = get_app_data_dir()
            data_dir = os.path.join(app_data_dir, "data")
            
            # Убедимся, что директория существует
            os.makedirs(data_dir, exist_ok=True)
            
            file_path = os.path.join(data_dir, filename)
            uploaded_file.save(file_path)
            
            # Проверяем, что файл действительно зашифрован и может быть прочитан с нашим ключом
            try:
                servers = decrypt_data(open(file_path, 'rb').read())
                json.loads(servers)  # Проверяем, что это корректный JSON
                flash('Файл данных успешно импортирован и прикреплен!', 'success')
            except (InvalidToken, json.JSONDecodeError, Exception) as e:
                # Удаляем файл, если он не может быть расшифрован
                os.remove(file_path)
                flash('Ошибка: файл не может быть расшифрован или поврежден. Возможно, он создан с другим ключом.', 'danger')
                return redirect(url_for('settings_page'))
            
            # Обновляем конфигурацию для использования нового файла
            app.config['active_data_file'] = file_path
            save_app_config()
            return redirect(url_for('settings_page'))
        else:
            flash('Неверный тип файла. Пожалуйста, выберите файл .enc', 'danger')
    except Exception as e:
        flash(f'Ошибка при импорте файла: {str(e)}', 'danger')
    return redirect(url_for('settings_page'))

@app.route('/data/import_external', methods=['POST'])
def import_external_data():
    global app_config
    try:
        uploaded_file = request.files['external_file']
        external_key = request.form.get('external_key', '').strip()
        
        if not uploaded_file or not external_key:
            flash('Необходимо выбрать файл и указать внешний ключ шифрования.', 'danger')
            return redirect(url_for('settings_page'))
            
        if not uploaded_file.filename.endswith('.enc'):
            flash('Неверный тип файла. Пожалуйста, выберите файл .enc', 'danger')
            return redirect(url_for('settings_page'))
        
        # Проверяем формат ключа (должен быть в формате Fernet)
        try:
            # Попытаемся создать экземпляр Fernet с предоставленным ключом
            # Это лучше, чем проверка префикса, так как ключи могут иметь разные префиксы
            test_fernet = Fernet(external_key.encode())
        except Exception:
            flash('Неверный формат ключа шифрования. Ключ должен быть действительным ключом Fernet.', 'danger')
            return redirect(url_for('settings_page'))
        
        # Создаем временный файл для проверки
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            uploaded_file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Пытаемся расшифровать файл с внешним ключом
            fernet_external = Fernet(external_key.encode())
            with open(temp_file_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = fernet_external.decrypt(encrypted_data)
            servers_data = json.loads(decrypted_data.decode('utf-8'))
            
            # Проверяем структуру данных
            if not isinstance(servers_data, list):
                raise ValueError("Неверная структура данных")
            
            # Данные корректны, теперь объединяем их с текущими данными
            current_servers = []
            current_file = get_active_data_path()
            
            # Загружаем текущие данные, если файл существует
            if current_file and os.path.exists(current_file):
                try:
                    with open(current_file, 'rb') as f:
                        current_encrypted = f.read()
                    # decrypt_data ожидает строку, поэтому декодируем bytes в строку
                    current_decrypted = fernet.decrypt(current_encrypted).decode('utf-8')
                    current_servers = json.loads(current_decrypted)
                except Exception:
                    current_servers = []
            
            # Получаем списки существующих IP адресов и имен для предотвращения дублей
            existing_ips = {server.get('ip', '') for server in current_servers if server.get('ip')}
            existing_names = {server.get('name', '') for server in current_servers if server.get('name')}
            
            # Находим максимальный ID среди существующих серверов
            max_id = 0
            for server in current_servers:
                if 'id' in server and isinstance(server['id'], int):
                    max_id = max(max_id, server['id'])
            
            # Фильтруем импортируемые сервера и присваиваем новые ID
            new_servers = []
            skipped_count = 0
            for server in servers_data:
                server_ip = server.get('ip', '')
                server_name = server.get('name', '')
                
                # Проверяем на дублирование по IP или имени
                if server_ip in existing_ips or server_name in existing_names:
                    skipped_count += 1
                    continue
                
                # Присваиваем новый уникальный ID
                max_id += 1
                server['id'] = max_id
                new_servers.append(server)
                
                # Добавляем в списки для отслеживания дублей
                if server_ip:
                    existing_ips.add(server_ip)
                if server_name:
                    existing_names.add(server_name)
            
            # Перешифровываем пароли в новых серверах с нашим ключом
            for server in new_servers:
                # Перешифровываем SSH пароли
                if 'ssh_credentials' in server:
                    if 'password' in server['ssh_credentials'] and server['ssh_credentials']['password']:
                        # Расшифровываем старым ключом
                        try:
                            fernet_external = Fernet(external_key.encode())
                            decrypted_password = fernet_external.decrypt(server['ssh_credentials']['password'].encode()).decode()
                            # Шифруем нашим ключом
                            server['ssh_credentials']['password'] = fernet.encrypt(decrypted_password.encode()).decode()
                        except Exception:
                            # Если не удалось расшифровать, оставляем как есть
                            pass
                    
                    if 'root_password' in server['ssh_credentials'] and server['ssh_credentials']['root_password']:
                        try:
                            fernet_external = Fernet(external_key.encode())
                            decrypted_root_password = fernet_external.decrypt(server['ssh_credentials']['root_password'].encode()).decode()
                            server['ssh_credentials']['root_password'] = fernet.encrypt(decrypted_root_password.encode()).decode()
                        except Exception:
                            pass
                
                # Перешифровываем пароли панели управления
                if 'panel_credentials' in server:
                    if 'password' in server['panel_credentials'] and server['panel_credentials']['password']:
                        try:
                            fernet_external = Fernet(external_key.encode())
                            decrypted_panel_password = fernet_external.decrypt(server['panel_credentials']['password'].encode()).decode()
                            server['panel_credentials']['password'] = fernet.encrypt(decrypted_panel_password.encode()).decode()
                        except Exception:
                            pass
                    
                    if 'user' in server['panel_credentials'] and server['panel_credentials']['user']:
                        try:
                            fernet_external = Fernet(external_key.encode())
                            decrypted_panel_user = fernet_external.decrypt(server['panel_credentials']['user'].encode()).decode()
                            server['panel_credentials']['user'] = fernet.encrypt(decrypted_panel_user.encode()).decode()
                        except Exception:
                            pass
                
                # Перешифровываем пароли кабинета хостера
                if 'hoster_credentials' in server:
                    if 'password' in server['hoster_credentials'] and server['hoster_credentials']['password']:
                        try:
                            fernet_external = Fernet(external_key.encode())
                            decrypted_hoster_password = fernet_external.decrypt(server['hoster_credentials']['password'].encode()).decode()
                            server['hoster_credentials']['password'] = fernet.encrypt(decrypted_hoster_password.encode()).decode()
                        except Exception:
                            pass
                    
                    if 'user' in server['hoster_credentials'] and server['hoster_credentials']['user']:
                        try:
                            fernet_external = Fernet(external_key.encode())
                            decrypted_hoster_user = fernet_external.decrypt(server['hoster_credentials']['user'].encode()).decode()
                            server['hoster_credentials']['user'] = fernet.encrypt(decrypted_hoster_user.encode()).decode()
                        except Exception:
                            pass
            
            # Объединяем данные
            combined_servers = current_servers + new_servers
            
            # Создаем новый файл с объединенными данными
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"merged_{timestamp}.enc"
            
            app_data_dir = get_app_data_dir()
            data_dir = os.path.join(app_data_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            
            file_path = os.path.join(data_dir, filename)
            
            # Шифруем объединенные данные нашим ключом
            json_string = json.dumps(combined_servers, ensure_ascii=False, indent=2)
            encrypted_with_our_key = fernet.encrypt(json_string.encode('utf-8'))
            with open(file_path, 'wb') as f:
                f.write(encrypted_with_our_key)
            
            # Обновляем конфигурацию
            app.config['active_data_file'] = file_path
            save_app_config()
            
            # Информируем пользователя о результате
            if new_servers:
                message = f'Успешно импортировано {len(new_servers)} новых серверов!'
                if skipped_count > 0:
                    message += f' Пропущено {skipped_count} дублирующихся серверов.'
                flash(message, 'success')
            else:
                flash('Все сервера из импортируемого файла уже существуют в вашем списке.', 'info')
            
        except InvalidToken:
            flash('Ошибка: неверный ключ шифрования. Проверьте правильность введенного ключа.', 'danger')
        except json.JSONDecodeError:
            flash('Ошибка: файл содержит некорректные данные.', 'danger')
        except Exception as e:
            flash(f'Ошибка при импорте: {str(e)}', 'danger')
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except Exception as e:
        flash(f'Ошибка при обработке файла: {str(e)}', 'danger')
    
    return redirect(url_for('settings_page'))

@app.route('/data/detach', methods=['POST'])
def detach_data():
    """Открепляет текущий файл данных."""
    if app.config.get('active_data_file'):
        app.config['active_data_file'] = None
        save_app_config()
        flash('Файл данных успешно откреплен.', 'info')
    
    return redirect(url_for('index'))


@app.route('/check_ip/<ip_address>')
def check_ip(ip_address):
    try:
        # Проверяем доступность интернета
        socket.create_connection(("8.8.8.8", 53), timeout=3)
    except OSError:
        return jsonify({
            "error": "Нет подключения к интернету",
            "message": "Проверка IP недоступна в офлайн режиме"
        }), 503
    
    try:
        ip_check_url = app.config.get('service_urls', {}).get('ip_check_api', 'https://ipinfo.io/{ip}/json').format(ip=ip_address)
        response = requests.get(ip_check_url, timeout=10)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                "error": f"Ошибка запроса: статус {response.status_code}",
                "message": "Сервис проверки IP временно недоступен"
            }), 500
    except requests.exceptions.Timeout:
        return jsonify({
            "error": "Превышено время ожидания",
            "message": "Сервис проверки IP не отвечает"
        }), 504
    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": "Ошибка подключения",
            "message": "Не удалось подключиться к сервису проверки IP"
        }), 503
    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": f"Ошибка запроса: {str(e)}",
            "message": "Проблема с подключением к сервису"
        }), 500

@app.route('/settings/change-key', methods=['POST'])
def change_main_key():
    """Смена главного ключа с перешифровкой всех данных."""
    global SECRET_KEY, fernet
    try:
        new_key = request.form.get('new_key', '').strip()
        confirm_key = request.form.get('confirm_key', '').strip()
        
        # Проверяем, что ключи совпадают
        if new_key != confirm_key:
            flash('Ошибка: ключи не совпадают.', 'danger')
            return redirect(url_for('settings_page'))
        
        # Проверяем формат нового ключа
        if not new_key:
            flash('Ошибка: новый ключ не может быть пустым.', 'danger')
            return redirect(url_for('settings_page'))
            
        try:
            # Проверяем, что новый ключ корректный для Fernet
            test_fernet = Fernet(new_key.encode())
        except Exception:
            flash('Ошибка: некорректный формат ключа. Ключ должен быть в формате Fernet.', 'danger')
            return redirect(url_for('settings_page'))
        
        # Загружаем текущие данные с существующим ключом
        current_servers = load_servers()
        
        # Создаем резервную копию с временной меткой
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_before_key_change_{timestamp}.enc"
        
        app_data_dir = get_app_data_dir()
        data_dir = os.path.join(app_data_dir, "data")
        backup_path = os.path.join(data_dir, backup_filename)
        
        # Создаем резервную копию
        if app.config.get('active_data_file') and os.path.exists(app.config['active_data_file']):
            shutil.copy2(app.config['active_data_file'], backup_path)
        
        # Сохраняем старый ключ для отката в случае ошибки
        old_key = os.environ.get('SECRET_KEY')
        
        # Устанавливаем новый ключ в переменной окружения
        os.environ['SECRET_KEY'] = new_key
        
        # КРИТИЧНО: Обновляем глобальные переменные ПЕРЕД перешифровкой
        SECRET_KEY = new_key
        fernet = Fernet(SECRET_KEY.encode())
        
        # Определяем правильный путь к .env файлу
        is_frozen = getattr(sys, 'frozen', False)
        if is_frozen:
            # Для упакованного приложения сохраняем .env в пользовательскую директорию
            env_file = os.path.join(APP_DATA_DIR, '.env')
        else:
            # Для разработки используем локальный .env
            env_file = '.env'
        
        env_lines = []
        
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
        
        # Обновляем или добавляем SECRET_KEY
        key_updated = False
        for i, line in enumerate(env_lines):
            if line.startswith('SECRET_KEY='):
                env_lines[i] = f'SECRET_KEY={new_key}\n'
                key_updated = True
                break
        
        if not key_updated:
            env_lines.append(f'SECRET_KEY={new_key}\n')
        
        # Создаем директорию если нужно
        os.makedirs(os.path.dirname(env_file), exist_ok=True)
        
        with open(env_file, 'w') as f:
            f.writelines(env_lines)
        
        # Создаем новый зашифрованный файл с новым ключом
        new_filename = f"servers_reencrypted_{timestamp}.enc"
        new_file_path = os.path.join(data_dir, new_filename)
        
        try:
            # Перешифровываем данные с новым ключом
            with open(new_file_path, 'wb') as f:
                f.write(encrypt_data(json.dumps(current_servers)).encode())
            
            # Обновляем конфигурацию приложения
            app.config['active_data_file'] = new_file_path
            save_app_config()
            
            flash(f'✅ Ключ успешно изменен! Создан новый файл данных: {new_filename}. Резервная копия сохранена как: {backup_filename}', 'success')
            
        except Exception as e:
            # Откатываем изменения в случае ошибки
            os.environ['SECRET_KEY'] = old_key
            
            # КРИТИЧНО: Откатываем глобальные переменные
            SECRET_KEY = old_key
            fernet = Fernet(SECRET_KEY.encode())
            
            # Восстанавливаем старый .env файл
            old_env_lines = []
            for line in env_lines:
                if line.startswith('SECRET_KEY='):
                    old_env_lines.append(f'SECRET_KEY={old_key}\n')
                else:
                    old_env_lines.append(line)
            
            with open(env_file, 'w') as f:
                f.writelines(old_env_lines)
            
            flash(f'Ошибка при перешифровке данных: {str(e)}. Изменения отменены.', 'danger')
            
    except Exception as e:
        flash(f'Ошибка при смене ключа: {str(e)}', 'danger')
    
    return redirect(url_for('settings_page'))

@app.route('/settings/verify-key-data', methods=['POST'])
def verify_key_data():
    """Проверка соответствия ключа и данных без импорта."""
    try:
        uploaded_file = request.files.get('verify_file')
        test_key = request.form.get('verify_key', '').strip()
        
        if not uploaded_file or not test_key:
            flash('Необходимо выбрать файл и указать ключ для проверки.', 'danger')
            return redirect(url_for('settings_page'))
        
        if not uploaded_file.filename.endswith('.enc'):
            flash('Неверный тип файла. Выберите файл .enc', 'danger')
            return redirect(url_for('settings_page'))
        
        # Проверяем формат ключа
        try:
            test_fernet = Fernet(test_key.encode())
        except Exception:
            flash('❌ Некорректный формат ключа Fernet.', 'danger')
            return redirect(url_for('settings_page'))
        
        # Читаем файл
        file_content = uploaded_file.read()
        
        try:
            # Пытаемся расшифровать
            decrypted_data = test_fernet.decrypt(file_content).decode()
            data = json.loads(decrypted_data)
            
            # Анализируем содержимое
            if isinstance(data, list):
                server_count = len(data)
                
                # Собираем информацию о серверах
                providers = set()
                server_names = []
                
                for server in data:
                    if isinstance(server, dict):
                        if 'provider' in server:
                            providers.add(server['provider'])
                        if 'name' in server:
                            server_names.append(server['name'])
                
                provider_list = ', '.join(sorted(providers)) if providers else 'Не указано'
                name_preview = ', '.join(server_names[:3])
                if len(server_names) > 3:
                    name_preview += f' и еще {len(server_names) - 3}'
                
                flash(f'✅ Ключ подходит! Найдено серверов: {server_count}. Провайдеры: {provider_list}. Серверы: {name_preview}', 'success')
            else:
                flash('✅ Ключ подходит, но структура данных неожиданная.', 'warning')
                
        except InvalidToken:
            flash('❌ Ключ не подходит к этому файлу данных.', 'danger')
        except json.JSONDecodeError:
            flash('❌ Файл расшифрован, но содержит некорректные JSON данные.', 'danger')
        except Exception as e:
            flash(f'❌ Ошибка при проверке: {str(e)}', 'danger')
            
    except Exception as e:
        flash(f'Ошибка при обработке файла: {str(e)}', 'danger')
    
    return redirect(url_for('settings_page'))

@app.route('/settings/generate-key', methods=['POST'])
def generate_new_key():
    """Генерация нового случайного ключа Fernet."""
    try:
        new_key = Fernet.generate_key().decode()
        return jsonify({'success': True, 'key': new_key})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/shutdown')
def shutdown():
    """Завершает работу сервера."""
    # Не используем стандартный метод, так как он может быть ненадежен
    # Вместо этого, отправляем сигнал главному потоку
    os.kill(os.getpid(), signal.SIGINT)
    return 'Сервер выключается...'

def run_flask():
    """Запускает Flask-приложение."""
    # debug=False и use_reloader=False важны для стабильной работы в потоке
    app.run(host='127.0.0.1', port=5050, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Выполняем проверку и миграцию при старте приложения
    migrate_data_if_needed()
    
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    def on_closing():
        print("Окно закрывается, отправка запроса на выключение...")
        try:
            # Отправляем запрос на выключение, чтобы корректно остановить сервер
            requests.get('http://127.0.0.1:5050/shutdown', timeout=1)
        except requests.exceptions.RequestException:
            # Это нормально, так как сервер умрет до получения ответа
            pass

    # Создаем окно PyWebView
    window = webview.create_window(
        'VPN Server Manager',
        'http://127.0.0.1:5050',
        width=1280,
        height=800,
        resizable=True
    )
    window.events.closing += on_closing

    # Запускаем GUI
    webview.start(debug=False) # debug=True может помочь с отладкой, если что-то пойдет не так

    # После закрытия окна PyWebView, главный поток продолжится здесь.
    print("Приложение закрыто.")