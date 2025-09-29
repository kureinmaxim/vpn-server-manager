# Система шифрования SECRET_KEY в VPN Server Manager

## 🔐 Назначение ключа

SECRET_KEY - это криптографический ключ, используемый для шифрования всех чувствительных данных в приложении:

- **Пароли SSH** серверов
- **Данные панелей управления** (логины, пароли)
- **Информация о хостингах** (учетные данные)
- **Все данные серверов** в файле `servers.json.enc`

## 🎲 Создание ключа

### Автоматическая генерация
```bash
python3 tools/generate_key.py
```

### Ручное создание
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())  # Сохраните в .env файл
```

## 📁 Хранение ключа

### Файл .env
```
SECRET_KEY=ваш_ключ_здесь
```

### Расположение файла
- **Режим разработки**: В корне проекта
- **Упакованное приложение**: `~/Library/Application Support/VPNServerManager/.env`

## ⚙️ Применение в приложении

### Инициализация
```python
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.environ.get('SECRET_KEY')
fernet = Fernet(SECRET_KEY.encode())
```

### Шифрование данных
```python
def encrypt_data(data):
    return fernet.encrypt(data.encode()).decode()

# Пример использования
encrypted_password = encrypt_data("mypassword123")
```

### Расшифровка данных
```python
def decrypt_data(encrypted_data):
    try:
        return fernet.decrypt(encrypted_data.encode()).decode()
    except:
        return ""

# Пример использования
password = decrypt_data(encrypted_password)
```

## 🔄 Смена ключа

### Процесс смены
1. Генерируется новый ключ
2. Создается резервная копия старых данных
3. Все данные перешифровываются новым ключом
4. Обновляется файл .env

### Код смены ключа
```python
# В функции change_main_key()
old_key = os.environ.get('SECRET_KEY')
new_key = request.form.get('new_key')

# Обновляем глобальные переменные
SECRET_KEY = new_key
fernet = Fernet(SECRET_KEY.encode())

# Перешифровываем все данные
servers = load_servers()  # Загружаем старыми ключом
save_servers(servers)     # Сохраняем новым ключом
```

## 🛡️ Безопасность

### Алгоритм шифрования
- **Fernet** (AES-128 + HMAC-SHA256)
- **Симметричное шифрование**
- **Аутентификация сообщений**

### Защита ключа
- Ключ НЕ хранится в Git
- Файл .env в .gitignore
- Автоматическое резервное копирование при смене

## ⚠️ Важные моменты

### Потеря ключа
- **Без ключа данные НЕВОЗМОЖНО восстановить**
- Всегда делайте резервные копии
- Используйте "Полный экспорт" для backup

### Проверка ключа
```python
# Проверка соответствия ключа и данных
try:
    decrypted_data = fernet.decrypt(encrypted_data)
    return True
except InvalidToken:
    return False
```

## 📋 Примеры использования

### В app.py
```python
# Шифрование пароля SSH
server['ssh_credentials']['password'] = encrypt_data(password)

# Расшифровка для отображения
decrypted_password = decrypt_data(server['ssh_credentials']['password'])
```

### В функциях экспорта
```python
# Экспорт ключа
with open('exported_key.env', 'w') as f:
    f.write(f'SECRET_KEY={SECRET_KEY}')
```

## 🔍 Отладка

### Проверка ключа
```bash
python3 tools/decrypt_tool.py
```

### Генерация нового ключа
```bash
python3 tools/generate_key.py
```

### Проверка соответствия
- В настройках приложения
- Функция "Проверить соответствие"
- Показывает количество серверов в файле 