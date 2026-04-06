# 🛠️ Руководство по сборке VPN Server Manager

## 📋 Требования

- Python 3.13+
- pip (менеджер пакетов Python)
- Git (опционально)
- Inno Setup (для сборки Windows инсталлятора)

## 🚀 Быстрый старт

### Windows

```powershell
# 1. Создание виртуального окружения
python -m venv venv

# 2. Активация
.\venv\Scripts\Activate.ps1

# 3. Установка зависимостей
python -m pip install -r requirements.txt

# 4. Первоначальная настройка
copy env.example .env
python generate_key.py
copy config\config.json.template config.json
```

### macOS / Linux

```bash
# 1. Создание виртуального окружения
python3 -m venv venv

# 2. Активация
source venv/bin/activate

# 3. Установка зависимостей
pip install -r requirements.txt

# 4. Первоначальная настройка
cp env.example .env
python3 generate_key.py
cp config/config.json.template config.json
```

## ⚙️ Конфигурация

### Обязательные шаги перед первым запуском

1. **Создайте `.env` файл**
   ```bash
   cp env.example .env
   ```

2. **Сгенерируйте секретный ключ**
   ```bash
   python generate_key.py
   ```

3. **Настройте конфигурацию**
   ```bash
   cp config/config.json.template config.json
   # Откройте config.json и измените PIN-код!
   ```

### Важные файлы конфигурации

| Файл | Содержит | Статус |
|------|----------|--------|
| `.env` | SECRET_KEY, DEFAULT_PIN | Не в Git |
| `config.json` | PIN-код, пути к данным | Не в Git |
| `data/*.enc` | Зашифрованные данные серверов | Не в Git |

## 🏃 Запуск приложения

### Режим разработки

**Windows:**
```powershell
# С активированным venv
python run.py

# Или напрямую
.\venv\Scripts\python.exe run.py
```

**macOS / Linux:**
```bash
# С активированным venv
python3 run.py

# Или напрямую
./venv/bin/python3 run.py
```

### Режим GUI (Desktop)

```bash
# Windows
python run_desktop.py

# macOS / Linux
python3 run_desktop.py
```

## 📦 Сборка инсталлятора

### Windows

**Способ 1: PowerShell скрипт**
```powershell
.\build_windows.ps1
```

**Способ 2: Batch файл**
```cmd
build_windows.bat
```

Требования:
- Установленный Inno Setup
- Все зависимости установлены в venv
- Выполнена первоначальная настройка

Результат: `installer_output\VPN-Server-Manager-Setup-v{version}.exe`

### macOS

```bash
python3 build_macos.py
```

Требования:
- py2app (`pip install py2app`)
- Все зависимости установлены

Результат: `.app` bundle в `dist/`

## 🐳 Docker

### Сборка образа

```bash
docker-compose build
```

### Запуск

```bash
docker-compose up -d
```

Приложение будет доступно на `http://localhost:5000`

## 🌍 Компиляция переводов

Перед сборкой инсталлятора или запуском приложения необходимо скомпилировать файлы переводов (`.po` → `.mo`):

### Компиляция всех переводов

```bash
# Windows (PowerShell)
python -m babel.messages.frontend compile -d translations

# macOS / Linux
pybabel compile -d translations
```

### Компиляция конкретного языка

```bash
# Английский
pybabel compile -d translations -l en

# Китайский
pybabel compile -d translations -l zh
```

### Обновление переводов (после изменений в коде)

```bash
# 1. Извлечь новые строки из кода
pybabel extract -F babel.cfg -o translations/messages.pot .

# 2. Обновить существующие .po файлы
pybabel update -i translations/messages.pot -d translations

# 3. Перевести новые строки в .po файлах (вручную или автоматически)
python tools/auto_translate_po.py

# 4. Скомпилировать в .mo
pybabel compile -d translations
```

### Структура файлов переводов

```
translations/
├── en/
│   └── LC_MESSAGES/
│       ├── messages.po   # Исходный файл переводов (редактируется)
│       └── messages.mo   # Скомпилированный файл (генерируется)
└── zh/
    └── LC_MESSAGES/
        ├── messages.po
        └── messages.mo
```

> ⚠️ **Важно:** Без `.mo` файлов переключение языков НЕ будет работать!

## 🧪 Тестирование

```bash
# Установка тестовых зависимостей
pip install pytest pytest-cov

# Запуск тестов
pytest

# С покрытием
pytest --cov=app tests/
```

## ⚠️ Решение проблем

### Проблема: "pip is not recognized" (Windows)

**Решение:**
```powershell
# Используйте python -m pip вместо pip
python -m pip install -r requirements.txt
```

### Проблема: ModuleNotFoundError

**Решение:**
```bash
# Убедитесь, что venv активирован и зависимости установлены
pip list
pip install -r requirements.txt
```

### Проблема: Ошибка импорта cryptography

**Решение:**
```bash
# Переустановите cryptography
pip uninstall cryptography
pip install cryptography
```

### Проблема: Порт 5000 занят

**Решение:**
```bash
# Измените порт в run.py или используйте переменную окружения
export FLASK_RUN_PORT=5001  # Linux/macOS
$env:FLASK_RUN_PORT=5001    # Windows PowerShell
```

### Проблема: Переключение языков не работает

**Причина:** Не скомпилированы `.mo` файлы переводов.

**Решение:**
```bash
# Скомпилировать переводы
python -m babel.messages.frontend compile -d translations
```

## 📚 Дополнительная информация

- [Руководство по версионированию](VERSION_MANAGEMENT.md)
- [Руководство по релизам](docs/release_guide.md)
- [Docker руководство](docs/DOCKER_GUIDE.md)
- [Windows руководство](docs/WINDOWS_GUIDE.md)

## 🔒 Безопасность

### ⚠️ Файлы, которые НЕ ДОЛЖНЫ попадать в Git

- `.env` - содержит SECRET_KEY
- `config.json` - содержит PIN-код
- `data/*.enc` - зашифрованные данные
- `*.key`, `*.pem` - ключи и сертификаты

### ✅ Проверка перед коммитом

```bash
# Проверить, что секреты не в индексе
git ls-files | grep -E "\.env$|config\.json$|\.enc$"
# Если команда что-то выводит - НЕ КОММИТЬТЕ!
```

## ✅ Чеклист перед запуском

- [ ] Создано виртуальное окружение
- [ ] Активировано виртуальное окружение
- [ ] Установлены все зависимости
- [ ] Создан `.env` файл
- [ ] Сгенерирован уникальный `SECRET_KEY`
- [ ] Создан `config.json` из шаблона
- [ ] Изменён PIN-код с 1234 на свой
- [ ] Приложение запускается без ошибок

