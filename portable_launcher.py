"""
Лаунчер для портативной версии VPN Server Manager
Обеспечивает работу приложения в портативном режиме,
сохраняя все данные в папках относительно исполняемого файла.
"""
import os
import sys
import configparser
from pathlib import Path
import webbrowser
import threading
import time
import subprocess

# Определяем корневую директорию (где находится исполняемый файл)
if getattr(sys, 'frozen', False):
    # Если запущен как скомпилированное приложение
    APP_DIR = Path(sys.executable).parent
else:
    # Если запущен как скрипт
    APP_DIR = Path(__file__).parent

# Пути для данных в портативной версии
DATA_DIR = APP_DIR / "data"
UPLOADS_DIR = APP_DIR / "uploads"
CONFIG_FILE = APP_DIR / "portable_config.ini"

# Создаем папки, если их нет
DATA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

# Проверяем, есть ли конфигурационный файл, если нет - создаем
if not CONFIG_FILE.exists():
    config = configparser.ConfigParser()
    config['Settings'] = {
        'Portable': '1',
        'DataPath': 'data',
        'UploadsPath': 'uploads'
    }
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

# Создаем .env файл, если его нет
ENV_FILE = APP_DIR / ".env"
if not ENV_FILE.exists():
    # Импортируем Fernet для генерации ключа
    try:
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        with open(ENV_FILE, 'w') as f:
            f.write(f"SECRET_KEY={key}\n")
            f.write("FLASK_SECRET_KEY=portable_app_key\n")
    except ImportError:
        with open(ENV_FILE, 'w') as f:
            f.write("SECRET_KEY=please_generate_proper_key_on_first_run\n")
            f.write("FLASK_SECRET_KEY=portable_app_key\n")

# Создаем пустой файл servers.json.enc, если его нет
ENC_FILE = DATA_DIR / "servers.json.enc"
if not ENC_FILE.exists():
    with open(ENC_FILE, 'wb') as f:
        pass  # Пустой файл

# Функция для запуска браузера после небольшой задержки
def open_browser():
    time.sleep(3)  # Даем Flask время запуститься
    webbrowser.open('http://127.0.0.1:5000')

def main():
    # Запускаем браузер в отдельном потоке
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Устанавливаем переменные окружения для Flask
    os.environ["FLASK_ENV"] = "portable"
    
    # Импортируем и запускаем основное приложение
    try:
        # Перенаправляем stderr чтобы скрыть вывод Flask в портативной версии
        original_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')
        
        # Теперь импортируем и запускаем Flask-приложение
        from app import app
        app.config['UPLOAD_FOLDER'] = str(UPLOADS_DIR)
        app.config['active_data_file'] = str(ENC_FILE)
        app.run(debug=False)
    except Exception as e:
        # В случае ошибки восстанавливаем stderr и выводим сообщение
        sys.stderr = original_stderr
        print(f"Ошибка при запуске приложения: {e}")
        input("Нажмите Enter для выхода...")

if __name__ == "__main__":
    main() 