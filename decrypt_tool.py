import os
import json
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

# --- Улучшенная версия скрипта для v4.0.0 ---

def decrypt_data(fernet_instance, encrypted_data):
    """
    Вспомогательная функция для расшифровки отдельных полей.
    Использует уже созданный экземпляр Fernet.
    """
    if not encrypted_data:
        return ""
    try:
        # Данные уже в виде байтов из JSON, но могут быть закодированы как строка
        # Убедимся, что работаем с байтами
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
        return fernet_instance.decrypt(encrypted_data).decode('utf-8')
    except (InvalidToken, Exception):
        return "Ошибка дешифровки поля!"

def decrypt_servers_file():
    """
    Расшифровывает файл с данными серверов и выводит его содержимое,
    включая вложенные и отдельно зашифрованные учетные данные.
    """
    # --- Шаг 1: Загрузка секретного ключа ---
    load_dotenv()
    secret_key = os.getenv("SECRET_KEY")

    if not secret_key:
        print("Ошибка: Не удалось найти SECRET_KEY в файле .env.")
        print("Пожалуйста, убедитесь, что файл .env находится в корневой папке проекта и содержит SECRET_KEY.")
        return

    try:
        fernet = Fernet(secret_key.encode())
    except Exception as e:
        print(f"Ошибка инициализации Fernet: {e}")
        return

    # --- Шаг 2: Чтение и основная расшифровка файла ---
    data_file_path = os.path.join("data", "servers.json.enc")
    if not os.path.exists(data_file_path):
        print(f"Ошибка: Файл данных не найден по пути: {data_file_path}")
        return

    try:
        with open(data_file_path, 'rb') as f:
            encrypted_data = f.read()

        if not encrypted_data:
            print("Файл данных пуст.")
            return

        decrypted_json = fernet.decrypt(encrypted_data).decode('utf-8')
        servers = json.loads(decrypted_json)

    except (InvalidToken, Exception) as e:
        print(f"Критическая ошибка при расшифровке основного файла: {e}")
        print("Проверьте, что SECRET_KEY верный и файл не поврежден.")
        return
    
    # --- Шаг 3: Детальный разбор и вывод данных ---
    print("--- Расшифрованные данные серверов ---")
    if not servers:
        print("Файл не содержит данных о серверах.")
        return
        
    for i, server in enumerate(servers):
        print(f"\n{'='*10} Сервер #{i + 1}: {server.get('name', 'N/A')} {'='*10}")
        print(f"  IP Адрес: {server.get('ip_address', 'N/A')}")
        
        # Данные SSH
        ssh = server.get('ssh_credentials', {})
        if ssh:
            print("\n  [+] Учетные данные SSH:")
            print(f"    - Пользователь: {ssh.get('user', 'N/A')}")
            print(f"    - Пароль: {decrypt_data(fernet, ssh.get('password'))}")
            print(f"    - Порт: {ssh.get('port', 'N/A')}")
            if ssh.get('root_login_allowed'):
                 print(f"    - Root Пароль: {decrypt_data(fernet, ssh.get('root_password'))}")

        # Данные панели управления
        panel = server.get('panel_credentials', {})
        panel_url = server.get('panel_url')
        if panel_url or panel.get('user'):
            print("\n  [+] Панель управления:")
            print(f"    - URL: {panel_url if panel_url else 'N/A'}")
            print(f"    - Пользователь: {decrypt_data(fernet, panel.get('user'))}")
            print(f"    - Пароль: {decrypt_data(fernet, panel.get('password'))}")

        # Данные кабинета хостера
        hoster = server.get('hoster_credentials', {})
        hoster_url = server.get('hoster_url')
        if hoster_url or hoster.get('user'):
            print("\n  [+] Кабинет хостера:")
            print(f"    - URL: {hoster_url if hoster_url else 'N/A'}")
            print(f"    - Пользователь: {decrypt_data(fernet, hoster.get('user'))}")
            print(f"    - Пароль: {decrypt_data(fernet, hoster.get('password'))}")

    print(f"\n{'='*10} Процесс завершен {'='*10}")
    print("Примечание: В v4.0.0 используется новая модульная архитектура.")
    print("Для запуска приложения используйте: python run.py")


if __name__ == "__main__":
    decrypt_servers_file() 