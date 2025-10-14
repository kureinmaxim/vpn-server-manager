# VPN Server Manager - Полная Документация v4.0.7

Современное Flask-приложение для управления VPN серверами с поддержкой desktop GUI, интернационализации, криптографии и параллельного запуска.

## 📋 Содержание

- [Последние обновления](#-последние-обновления)
- [Архитектура](#️-архитектура)
- [Структура проекта](#-подробная-структура-проекта)
- [Ключевые компоненты](#-ключевые-компоненты)
- [Быстрый старт](#-быстрый-старт)
- [Запуск приложения](#-запуск-приложения)
- [Разработка](#️-разработка)
- [Docker](#-docker)
- [Интернационализация](#-интернационализация)
- [Сборка](#-сборка)
- [Конфигурация](#-конфигурация)
- [Тестирование](#-тестирование)
- [Безопасность](#-безопасность)
- [Логирование](#-логирование)
- [Архитектурные преимущества](#-архитектурные-преимущества)
- [Пути данных](#-пути-данных)
- [Multi-App Support](#-multi-app-support)
- [История версий](#-история-версий)

---

## ✅ Последние обновления

### v4.0.7 (13 октября 2025)
- 🔒 **КРИТИЧЕСКОЕ обновление безопасности**: Удалены конфиденциальные файлы (.env, config.json, *.enc) из всей истории Git
- 🔐 **Новый SECRET_KEY**: Сгенерирован безопасный ключ шифрования
- 📝 **config.json теперь локальный**: Добавлен в .gitignore, создан config.json.example как шаблон
- 🛡️ **Документация по безопасности**: Полное руководство в SECURITY.md
- ⚙️ **build_macos.py исправлен**: DMG больше не содержит конфиденциальные файлы
- 📋 **Обновлены шаблоны**: env.example и config.json.example с комментариями

### v4.0.5 (12 октября 2025)
- 🐛 **Функция "Сохранить как PNG"**: Полностью реализована функция сохранения статистики сервера в PNG
- 🔐 **PIN аутентификация**: Исправлено отображение ошибки при неправильном PIN
- 🌐 **SSH подключение**: Добавлена поддержка нестандартных SSH портов (2222)
- 🌍 **Переводы**: Добавлены новые строки перевода для английского и китайского языков

### v4.0.4 (12 октября 2025)
- 🪟 **Поддержка Windows**: Автоматические скрипты для упрощения установки и запуска на Windows
- 📖 **Документация для Windows**: Создано подробное руководство README_WINDOWS.md
- 🐳 **Улучшена Docker документация**: Обновлен DOCKER_GUIDE.md

### v4.0.3 (12 октября 2025)
- 🎯 **Единая версия**: Версия приложения автоматически загружается из `config.json`
- 🔧 **Централизованное управление**: Все компоненты используют версию из одного источника
- 📦 **Упрощённая сборка**: `setup.py` и `build_macos.py` читают версию динамически
- 🐛 **Критические исправления для frozen режима**:
  - Правильные пути для логов: `~/Library/Logs/VPNServerManager/`
  - Правильные пути для данных: `~/Library/Application Support/VPNServerManager-Clean/`
  - Корректный запуск из Finder (двойной клик на .app)
- 💡 **Умная конфигурация**: При первом запуске собранного приложения автоматическая настройка
- 🎨 **Иконка восстановлена**: PNG → ICNS конвертация с правильными размерами
- 🪟 **Desktop launcher**: Новый `launch_gui.py` для стабильного запуска
- 🚪 **Система выхода**: Полностью рабочий механизм выхода из desktop приложения
  - Новые endpoints: `/pin/exit_app`, `/pin/logout`, `/pin/check_auth`
  - Корректное закрытие pywebview через `window.destroy()`
  - Graceful shutdown с очисткой сессий
- 🔐 **Управление сессиями**: Исправлена проблема с постоянными сессиями
  - `private_mode=True` в pywebview
  - Сессии не сохраняются между запусками
  - PIN требуется при каждом запуске
- 🎨 **UI/UX улучшения**:
  - Увеличена высота окна на 10% (880px вместо 800px)
  - Исправлена видимость текста в футере для светлой темы
  - Информация о сервере (URL и порт) отображается в футере
- 🌐 **i18n**: Добавлены недостающие переводы (EN, ZH)
- 🔧 **Исправления маршрутов**: Страница "Управление подсказками" теперь работает

### v4.0.2 (12 октября 2025)
- 🚀 **Multi-App Support**: Параллельный запуск нескольких экземпляров без конфликтов
- 🎯 **Динамические порты**: WSGI сервер автоматически получает свободный порт от ОС
- 🔒 **Изолированные сессии**: Уникальные cookie (`vpn_manager_session_clean`) для каждого экземпляра
- ⚡ **Graceful Shutdown**: Эндпоинт `/shutdown` и обработчик закрытия окна
- 📚 **Документация**: Полная спецификация в [MULTI_APP_IMPLEMENTATION.md](MULTI_APP_IMPLEMENTATION.md)

### v4.0.1 (11 октября 2025)
- 🔐 **Исправлена проблема входа по PIN**: JavaScript в `layout.html` теперь отправляет данные в правильном формате JSON
- 📚 **Обновлена документация**: Добавлены технические отчеты и ссылки на исправления

---

## 🏗️ Архитектура

Проект следует принципам чистой архитектуры и использует:

- **Application Factory Pattern** для создания Flask-приложения
- **Service Layer** для изоляции бизнес-логики
- **Blueprint Pattern** для модульности
- **Dependency Injection** для управления зависимостями
- **Custom Exceptions** для обработки ошибок
- **Structured Logging** для мониторинга
- **Multi-App Support (v4.0.2)** для параллельного запуска без конфликтов
- **Centralized Versioning (v4.0.3)** версия из config.json

---

## 📁 Подробная структура проекта

```
VPNserverManage-Clean/
│
├── run.py                       # Новая точка входа (web/desktop режимы)
├── launch_gui.py                # 🆕 Desktop launcher для Finder (v4.0.3)
├── run_desktop.py               # Обёртка для --desktop режима
├── config.json.example          # 🆕 Шаблон конфигурации (v4.0.7)
├── config.json                  # 🎯 Конфигурация + версия 4.0.7 (не в Git)
├── Info.plist.template          # 🆕 Шаблон для macOS (v4.0.3)
│
├── app/                         # Основное приложение (модульная архитектура)
│   ├── __init__.py             # Application Factory + уникальные cookie-сессии
│   ├── config.py               # Конфигурация через переменные окружения
│   ├── exceptions.py           # Кастомные исключения
│   ├── models/                 # Модели данных
│   │   ├── __init__.py
│   │   └── server.py
│   ├── services/               # Бизнес-логика (Service Layer)
│   │   ├── __init__.py
│   │   ├── ssh_service.py      # SSH/SFTP сервисы + Connection Pooling
│   │   ├── crypto_service.py   # Криптографические операции
│   │   ├── api_service.py      # HTTP API сервисы
│   │   └── data_manager_service.py  # Управление данными (v4.0.1+)
│   ├── routes/                 # Маршруты (Blueprint Architecture)
│   │   ├── __init__.py
│   │   ├── main.py             # + эндпоинт /shutdown (v4.0.2)
│   │   └── api.py              # + Rate Limiting (v4.0.7)
│   └── utils/                  # Утилиты
│       ├── __init__.py
│       ├── validators.py
│       ├── decorators.py
│       └── rate_limiter.py     # 🆕 Rate Limiting (v4.0.7)
│
├── desktop/                    # Desktop GUI слой
│   ├── __init__.py
│   └── window.py               # WSGI сервер + динамические порты (v4.0.2)
│
├── tests/                      # Тесты
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_services/
│   └── test_routes/
│
├── build_macos.py              # Сборка .app и .dmg для macOS (v4.0.7: без секретов)
├── requirements.txt            # Зависимости Python
├── env.example                 # 🆕 Пример переменных окружения (v4.0.7)
├── setup.py                    # Установка пакета
├── Makefile                    # Команды разработки
├── Dockerfile                  # Контейнеризация
├── docker-compose.yml          # Docker Compose
├── pytest.ini                 # Настройки тестов
├── VPNServerManager-Clean.spec # Конфиг PyInstaller
├── README.md                   # Главная страница проекта
├── PROJECT_DOCUMENTATION.md    # Полная документация (этот файл)
├── MULTI_APP_IMPLEMENTATION.md # Спецификация Multi-App Support
├── ArchitecturalRules.md       # Архитектурные правила проекта
├── CHANGELOG.md                # История изменений
├── SECURITY.md                 # 🆕 Документация по безопасности (v4.0.7)
├── LICENSE                     # Лицензия MIT
├── .gitignore                  # Исключения для Git (обновлен v4.0.7)
├── generate_key.py             # Утилита генерации SECRET_KEY
├── decrypt_tool.py             # Инструмент для расшифровки данных
├── test_basic.py               # Базовые тесты
├── pin_auth.py                 # Система PIN-аутентификации (legacy)
├── pin_block_state.json        # Состояние блокировки PIN-кода
│
├── data/                       # Данные проекта (зашифрованные, НЕ В GIT v4.0.7)
│   ├── servers.json.enc
│   ├── hints.json
│   └── merged_*.enc
│
├── static/                     # Статические файлы
│   ├── css/
│   │   ├── style.css
│   │   ├── bootstrap.min.css
│   │   ├── bootstrap-icons.min.css
│   │   └── monitoring.css      # 🆕 Стили мониторинга (v4.0.7)
│   ├── images/
│   ├── fonts/
│   └── js/
│       └── bootstrap.bundle.min.js
│
├── templates/                  # HTML-шаблоны интерфейса
│   ├── layout.html
│   ├── index.html
│   ├── index_locked.html
│   ├── add_server.html
│   ├── edit_server.html
│   ├── settings.html
│   ├── about.html
│   ├── help.html
│   ├── cheatsheet.html
│   ├── manage_hints.html
│   └── monitoring.html         # 🆕 Страница мониторинга (v4.0.7)
│
├── translations/               # Переводы (.po/.mo)
│   ├── en/LC_MESSAGES/messages.{po,mo}
│   ├── zh/LC_MESSAGES/messages.{po,mo}
│   └── ru/LC_MESSAGES/         # (опционально)
│
├── docs/
│   ├── project_info/            # Основная документация проекта
│   │   ├── README.md
│   │   ├── SECRET_KEY.md
│   │   ├── BUILD.md
│   │   ├── BACKUP_TOOLS.md
│   │   └── maintenance/         # Документы по обслуживанию
│   │       └── quick_cleanup.md
│   │
│   └── lessons/                 # Учебные материалы
│       ├── i18n/                # Документация по локализации
│       │   ├── README.md
│       │   ├── flask-babel.md
│       │   ├── babel-cli-workflow.md
│       │   ├── auto-translate.md
│       │   ├── add-language.md
│       │   ├── troubleshooting.md
│       │   └── pyinstaller.md
│       │
│       ├── github_docs/         # Документация для GitHub
│       │   ├── CODE_OF_CONDUCT.md
│       │   ├── CONTRIBUTING.md
│       │   └── SECURITY.md
│       │
│       ├── github_tutorials/    # Туториалы по GitHub
│       │   ├── github_basics_tutorials/
│       │   └── github_cli_tutorials/
│       │
│       └── github-actions/      # Документация по GitHub Actions
│           ├── README.md
│           ├── PROJECT_USAGE.md
│           ├── GITHUB_ACTIONS_INDEX.md
│           ├── GITHUB_ACTIONS_FAQ.md
│           ├── GITHUB_ACTIONS_LESSONS.md
│           └── cleanup_summary.md
│
├── tools/
│   └── auto_translate_po.py     # Скрипт автоперевода `.po`
│
├── backup_tools/
│   ├── README.md
│   ├── QUICK_START.md
│   ├── INDEX.md
│   ├── CHANGE_CHECKLIST.md
│   ├── CURRENT_STATE.md
│   ├── BACKUP_SUMMARY.md
│   ├── FINAL_REPORT.md
│   ├── backup_strategy.md
│   └── rollback.sh              # Скрипт отката (поддерживает -y)
│
├── dist/                        # Результаты сборки (.app, .dmg)
├── build/                       # Временные файлы сборки
├── uploads/                     # Загруженные пользователем файлы
├── logs/                        # Логи приложения
└── venv/                        # Виртуальное окружение Python
```

---

## 🔧 Ключевые компоненты

### Application Factory Pattern
- **Файл**: `app/__init__.py`
- **Функция**: `create_app(config_name)`
- **Назначение**: Создание Flask-приложения с различными конфигурациями
- **v4.0.2**: Уникальные cookie-сессии (`SESSION_COOKIE_NAME = 'vpn_manager_session_clean'`)

### Service Layer
- **SSH Service**: `app/services/ssh_service.py` - SSH/SFTP операции + Connection Pooling (v4.0.7)
- **Crypto Service**: `app/services/crypto_service.py` - Шифрование/дешифрование
- **API Service**: `app/services/api_service.py` - HTTP запросы
- **Data Manager Service**: `app/services/data_manager_service.py` - Управление данными (v4.0.1+)
- **Registry**: `app/services/__init__.py` - Dependency Injection

### Blueprint Architecture
- **Main Blueprint**: `app/routes/main.py`
  - Основные маршруты
  - `/shutdown` (v4.0.2) - Graceful shutdown
  - `/manage_hints`, `/add_hint`, `/delete_hint` (v4.0.3) - Управление подсказками
  - `/monitoring/<server_id>` (v4.0.7) - Страница мониторинга
- **API Blueprint**: `app/routes/api.py`
  - REST API endpoints
  - `/api/monitoring/*` (v4.0.7) - API мониторинга с Rate Limiting
- **PIN Blueprint**: `app/routes/api.py`
  - PIN аутентификация
  - `/logout`, `/exit_app`, `/check_auth` (v4.0.3)

### Models
- **Server Model**: `app/models/server.py` - Модель сервера с валидацией

### Utils
- **Validators**: `app/utils/validators.py` - Валидация данных
- **Decorators**: `app/utils/decorators.py` - Декораторы безопасности
- **Rate Limiter**: `app/utils/rate_limiter.py` - 🆕 Rate Limiting (v4.0.7)

### Desktop Layer
- **Desktop App**: `desktop/window.py` - PyWebView GUI
- **WSGI сервер**: Динамическое выделение портов (порт 0)
- **Глобальные переменные**: `SERVER_PORT`, `_WSGI_SERVER`
- **Graceful Shutdown**: Корректное завершение с освобождением ресурсов
- **Exit System (v4.0.3)**: Закрытие через `/pin/exit_app` → `window.destroy()` → `os._exit(0)`
- **Session Management (v4.0.3)**: `private_mode=True`, сессии не персистентны
- **Window Size (v4.0.3)**: Увеличенное окно 880px (вместо 800px)

### Testing
- **Test Configuration**: `tests/conftest.py` - Pytest конфигурация
- **Service Tests**: `tests/test_services/` - Тесты сервисов
- **Route Tests**: `tests/test_routes/` - Тесты маршрутов

---

## 🚀 Быстрый старт

### 1. Клонирование и установка

```bash
git clone <repository-url>
cd VPNserverManage-Clean
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### 2. Настройка окружения

```bash
# Скопируйте шаблоны конфигурации
cp env.example .env
cp config.json.example config.json

# Сгенерируйте SECRET_KEY
python generate_key.py

# Отредактируйте .env файл с вашими настройками
nano .env
```

### 3. Запуск

```bash
# Web режим (автоматический выбор порта)
python run.py
# 🌐 VPN Server Manager v4.0.7 (версия из config.json)
# 📡 Web server: http://127.0.0.1:5000 (или следующий свободный)

# Desktop режим (динамический порт v4.0.7)
python run.py --desktop
# 🚀 Flask сервер запущен на http://127.0.0.1:XXXXX

# Debug режим
python run.py --debug
```

---

## 🖥️ Запуск приложения

### Web режим (с автоматическим выбором порта)
```bash
python run.py
# 🌐 VPN Server Manager v4.0.7
# 📡 Web server: http://127.0.0.1:5000 (или следующий свободный)
```

### Desktop режим (с динамическим портом v4.0.7)
```bash
python run.py --desktop
# 🚀 Flask сервер запущен на http://127.0.0.1:XXXXX
# Порт назначается автоматически ОС!
```

### Debug режим
```bash
python run.py --debug
```

### 🎯 Параллельный запуск (v4.0.2+)
```bash
# Терминал 1
python run.py --desktop  # Порт: 52341

# Терминал 2
python run.py --desktop  # Порт: 52342 (автоматически!)

# Результат: Два независимых экземпляра без конфликтов!
```

---

## 🛠️ Разработка

### Установка зависимостей для разработки

```bash
make install-dev
```

### Запуск тестов

```bash
make test              # Обычные тесты
make test-cov          # С покрытием кода
```

### Проверка качества кода

```bash
make lint              # Линтеры
make format            # Форматирование
make check-security    # Проверка безопасности
```

### Все проверки

```bash
make all
```

### Makefile команды

- `make install-dev` - Установка зависимостей для разработки
- `make test` - Запуск тестов
- `make lint` - Проверка качества кода
- `make format` - Форматирование кода
- `make all` - Все проверки

---

## 🐳 Docker

### Сборка и запуск

```bash
# Сборка образа
docker build -t vpn-manager-clean .

# Запуск
docker run -p 5000:5000 vpn-manager-clean

# Или с docker-compose
docker-compose up
```

### Разработка с Docker

```bash
docker-compose --profile dev up
```

### Docker файлы
- `Dockerfile` - Контейнеризация приложения
- `docker-compose.yml` - Оркестрация сервисов

---

## 🌐 Интернационализация

### Инициализация переводов

```bash
make init-translations
```

### Обновление переводов

```bash
make update-translations
```

### Компиляция переводов

```bash
make compile-translations
# или напрямую
pybabel compile -d translations
```

### Автоматический перевод

```bash
python tools/auto_translate_po.py
```

### Поддерживаемые языки
- 🇷🇺 Русский (ru) - по умолчанию
- 🇬🇧 Английский (en)
- 🇨🇳 Китайский (zh)

**Примечание**: Для упаковки в `.app` добавляйте `translations` в сборку (см. `docs/lessons/i18n/pyinstaller.md`)

---

## 📦 Сборка

### Создание исполняемого файла

```bash
make build
```

### Создание дистрибутива (macOS)

```bash
# Сборка .app и .dmg
python build_macos.py

# Результат:
# - dist/VPNServerManager-Clean.app
# - dist/VPNServerManager-Clean-v4.0.7.dmg
```

### PyInstaller

```bash
pyinstaller VPNServerManager-Clean.spec
```

**v4.0.7**: DMG больше не содержит конфиденциальные файлы (.env, config.json, *.enc)

---

## 🔧 Конфигурация

### Переменные окружения (.env)

```env
# Секретный ключ Flask (ОБЯЗАТЕЛЬНО!)
SECRET_KEY=your-secret-key-here

# Настройки интернационализации
BABEL_DEFAULT_LOCALE=ru
BABEL_SUPPORTED_LOCALES=ru,en,zh

# Настройки приложения
APP_VERSION=4.0.7
DATA_DIR=data
SERVERS_FILE=servers.json.enc

# Настройки логирования
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### Конфигурация (config.json)

```json
{
  "version": "4.0.7",
  "pin_code": "your-pin-hash",
  "language": "ru",
  "theme": "dark"
}
```

**⚠️ ВАЖНО (v4.0.7)**:
- `config.json` больше НЕ в Git
- Используйте `config.json.example` как шаблон
- Сгенерируйте новый `SECRET_KEY` через `generate_key.py`

---

## 🧪 Тестирование

### Структура тестов

- `tests/test_services/` - Тесты сервисов
- `tests/test_routes/` - Тесты маршрутов
- `conftest.py` - Фикстуры pytest

### Запуск тестов

```bash
pytest                    # Все тесты
pytest tests/test_services/  # Только сервисы
pytest -v                 # Подробный вывод
pytest --cov=app          # С покрытием
```

### Конфигурация

- `pytest.ini` - Настройки тестов
- Покрытие кода и интеграционные тесты

---

## 🔒 Безопасность

### ⚠️ Критическое обновление v4.0.7

**Удалены из Git**:
- `.env` - переменные окружения
- `config.json` - конфигурация приложения
- `data/*.enc` - зашифрованные данные

**Новые шаблоны**:
- `env.example` - пример переменных окружения
- `config.json.example` - пример конфигурации

### Проверка безопасности

```bash
bandit -r app
```

### Рекомендации

1. ✅ Всегда используйте HTTPS в production
2. ✅ Храните секреты в переменных окружения
3. ✅ Регулярно обновляйте зависимости
4. ✅ Используйте сильные пароли и PIN коды
5. ✅ Шифруйте чувствительные данные
6. ✅ **НИКОГДА не коммитьте** `.env`, `config.json`, `*.enc` в Git
7. ✅ Генерируйте уникальный `SECRET_KEY` для каждого развертывания

### Документация по безопасности

См. подробнее: [SECURITY.md](SECURITY.md)

---

## 📝 Логирование

### Расположение логов

Логи сохраняются в директории `logs/`:

- `app.log` - Основные логи приложения
- Ротация логов каждые 10MB
- Хранение до 10 файлов

### Production пути (macOS frozen .app)

- **Логи**: `~/Library/Logs/VPNServerManager/app.log`

### Development пути

- **Логи**: `./logs/app.log`

---

## 🎯 Архитектурные преимущества

### Multi-App Support (v4.0.2+)

#### ✅ Динамические порты
```python
# WSGI сервер с автоматическим выделением порта
_WSGI_SERVER = make_server('127.0.0.1', 0, app)
SERVER_PORT = _WSGI_SERVER.server_port
```

Никогда не будет конфликтов "Address already in use"!

#### ✅ Изолированные сессии
```python
# Уникальное имя cookie
app.config['SESSION_COOKIE_NAME'] = 'vpn_manager_session_clean'
```

#### ✅ Graceful Shutdown
```python
# Эндпоинт для корректного завершения
@main_bp.route('/shutdown')
def shutdown():
    os.kill(os.getpid(), signal.SIGINT)
    return 'Сервер выключается...', 200
```

### Exit System & Session Management (v4.0.3)

- ✅ **Система выхода**: Endpoints `/pin/logout` и `/pin/exit_app`
- ✅ **Проверка аутентификации**: Endpoint `/pin/check_auth`
- ✅ **Закрытие приложения**: JavaScript → `/pin/exit_app` → `window.destroy()` → `os._exit(0)`
- ✅ **Управление сессиями**: `private_mode=True`, `session.permanent=False`
- ✅ **Локализация**: Диалоги выхода и закрытия полностью переведены

### UI/UX Improvements (v4.0.3)

- ✅ **Увеличенное окно**: 880px вместо 800px для удобства
- ✅ **Футер**: Отображение URL и порта сервера
- ✅ **Светлая тема**: Исправлена видимость текста в футере
- ✅ **i18n**: Полная локализация всех диалогов

### Monitoring System (v4.0.7)

- ✅ **SSH Connection Pooling**: Повторное использование SSH соединений
- ✅ **Rate Limiting**: Защита от перегрузки API (10 req/мин)
- ✅ **Graceful Shutdown**: Закрытие всех SSH соединений при выходе
- ✅ **Error Handling**: Автоматическая остановка при потере соединения
- ✅ **System Stats**: Эндпоинт статистики системы мониторинга
- ✅ **Health Check**: Эндпоинт проверки работоспособности

### Технические детали

- **WSGI**: `wsgiref.simple_server.make_server('127.0.0.1', 0, app)`
- **Cookie**: `SESSION_COOKIE_NAME = 'vpn_manager_session_clean'`
- **Shutdown**: Эндпоинт `/shutdown` + обработчик `on_closing`
- **Exit**: `logout()` → `session.clear()` → `window.destroy()` → `os._exit(0)`
- **Session**: `private_mode=True`, отключен `SESSION_TYPE='filesystem'`
- **SSH Pool**: `SSHService._connection_pool` с `_pool_lock`
- **Rate Limit**: `RateLimiter(max_requests=10, time_window=60)`

### Преимущества

- ✅ Никогда не будет конфликтов "Address already in use"
- ✅ Неограниченное количество экземпляров
- ✅ Изолированные данные и сессии
- ✅ Корректное освобождение ресурсов
- ✅ Эффективное использование SSH соединений
- ✅ Защита от перегрузки серверов

---

## 📂 Пути данных

### Production (macOS frozen .app)

- **Данные**: `~/Library/Application Support/VPNServerManager-Clean/data/`
- **Логи**: `~/Library/Logs/VPNServerManager/app.log`
- **Загрузки**: `~/Library/Application Support/VPNServerManager-Clean/uploads/`
- **Конфигурация**: Встроена в .app bundle

### Development (исходники)

- **Данные**: `./data/`
- **Логи**: `./logs/app.log`
- **Загрузки**: `./uploads/`
- **Конфигурация**: `./config.json`

### Frozen режим (v4.0.3)

- **Launcher**: `launch_gui.py` - автоматическое логирование и инициализация
- **Detection**: `sys.frozen` для определения режима
- **Info.plist**: `NSPrincipalClass=NSApplication` для GUI
- **Иконка**: `icon_clean.icns` (16x16 → 1024x1024)

---

## 🔄 Миграция со старой структуры

Для миграции с монолитного `app.py`:

1. Создайте резервную копию данных
2. Установите новую структуру
3. Импортируйте данные через API
4. Проверьте все функции

---

## 📊 Мониторинг

### Возможности системы мониторинга (v4.0.7)

- ✅ Структурированное логирование
- ✅ Health checks для Docker
- ✅ Метрики производительности
- ✅ Отслеживание ошибок
- ✅ SSH Connection Pooling
- ✅ Rate Limiting API
- ✅ System Stats endpoint
- ✅ Health Check endpoint

### Документация мониторинга

- **[MONITORING_COMPLETE_CHECKLIST.md](MONITORING_COMPLETE_CHECKLIST.md)** - Чеклист безопасности (ЧИТАТЬ ПЕРВЫМ!)
- **[MONITORING_COMPLETE_GUIDE.md](MONITORING_COMPLETE_GUIDE.md)** - Полная документация
- **[README_MONITORING.md](README_MONITORING.md)** - Руководство пользователя

---

## 🚀 Multi-App Support (v4.0.2)

### Возможности параллельного запуска

#### ✅ Динамические порты
```python
# WSGI сервер с автоматическим выделением порта
_WSGI_SERVER = make_server('127.0.0.1', 0, app)
SERVER_PORT = _WSGI_SERVER.server_port
```

#### ✅ Изолированные сессии
```python
# Уникальное имя cookie
app.config['SESSION_COOKIE_NAME'] = 'vpn_manager_session_clean'
```

#### ✅ Graceful Shutdown
```python
# Эндпоинт для корректного завершения
@main_bp.route('/shutdown')
def shutdown():
    os.kill(os.getpid(), signal.SIGINT)
    return 'Сервер выключается...', 200
```

### Документация

Полная спецификация: [MULTI_APP_IMPLEMENTATION.md](MULTI_APP_IMPLEMENTATION.md)

---

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Добавьте тесты
5. Убедитесь, что все тесты проходят
6. Создайте Pull Request

См. также: [CONTRIBUTING.md](docs/lessons/github_docs/CONTRIBUTING.md)

---

## 🆘 Поддержка

При возникновении проблем:

1. Проверьте логи в `logs/app.log` (или `~/Library/Logs/VPNServerManager/app.log` для .app)
2. Убедитесь, что все зависимости установлены
3. Проверьте настройки в `.env` и `config.json`
4. Создайте issue в репозитории

---

## 🎯 История версий

### Релизы

- **v4.0.7** (13.10.2025) - 🔒 **КРИТИЧЕСКОЕ обновление безопасности**, система мониторинга
- **v4.0.5** (12.10.2025) - Исправления PNG сохранения, PIN ошибок, SSH портов, переводы
- **v4.0.4** (12.10.2025) - Поддержка Windows, Docker документация, Git конфигурация
- **v4.0.3** (12.10.2025) - Централизованная версия + критические исправления для macOS frozen режима
- **v4.0.2** (12.10.2025) - Multi-App Support, динамические порты, изолированные сессии
- **v4.0.1** (11.10.2025) - Исправление PIN аутентификации
- **v4.0.0** (15.01.2025) - Полная реструктуризация архитектуры

### 🔧 Ключевые исправления v4.0.7

#### Безопасность
- ✅ Удалены конфиденциальные файлы из истории Git
- ✅ Новый SECRET_KEY сгенерирован
- ✅ config.json добавлен в .gitignore
- ✅ Созданы шаблоны: env.example, config.json.example
- ✅ build_macos.py исправлен (DMG без секретов)
- ✅ Документация SECURITY.md

#### Мониторинг
- ✅ SSH Connection Pooling реализован
- ✅ Rate Limiting добавлен (10 req/60s)
- ✅ Graceful shutdown для SSH соединений
- ✅ JavaScript error handling с auto-stop
- ✅ System stats endpoint (`/api/monitoring/stats/system`)
- ✅ Health check endpoint (`/api/monitoring/health`)
- ✅ Rate limit logging (каждое 10-е блокирование)
- ✅ Safe cron job с `flock`
- ✅ UFW safety warnings (критично!)

### 🔧 Ключевые исправления v4.0.5
- ✅ Функция "Сохранить как PNG" полностью работает
- ✅ PIN ошибки показывают правильный текст
- ✅ Поддержка нестандартных SSH портов (2222)
- ✅ Все переводы обновлены (RU, EN, ZH)

### 🔧 Ключевые исправления v4.0.3
- ✅ Приложение запускается из Finder (двойной клик)
- ✅ Правильные пути для логов и данных в frozen режиме
- ✅ Иконка корректно отображается
- ✅ `launch_gui.py` - стабильный launcher с логированием
- ✅ Полностью рабочий механизм выхода из приложения
- ✅ Сессии не сохраняются между запусками (требуется PIN)
- ✅ Локализованные диалоги (выход, закрытие)
- ✅ Исправлена страница "Управление подсказками"
- ✅ Увеличенное окно (880px) для удобства
- ✅ Отображение URL и порта в футере

---

## 📄 Лицензия

MIT License - см. файл [LICENSE](LICENSE)

---

## 📚 Дополнительная документация

### Основные документы

- **[README.md](README.md)** - Главная страница проекта
- **[PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)** - Полная документация (этот файл)
- **[SECURITY.md](SECURITY.md)** - 🆕 Документация по безопасности
- **[CHANGELOG.md](CHANGELOG.md)** - История изменений
- **[MULTI_APP_IMPLEMENTATION.md](MULTI_APP_IMPLEMENTATION.md)** - Спецификация Multi-App Support
- **[ArchitecturalRules.md](ArchitecturalRules.md)** - Архитектурные правила

### Мониторинг

- **[MONITORING_COMPLETE_CHECKLIST.md](MONITORING_COMPLETE_CHECKLIST.md)** - ⚠️ Чеклист безопасности (ЧИТАТЬ ПЕРВЫМ!)
- **[MONITORING_COMPLETE_GUIDE.md](MONITORING_COMPLETE_GUIDE.md)** - Полная документация системы мониторинга
- **[README_MONITORING.md](README_MONITORING.md)** - Руководство пользователя по мониторингу

### Разработка

- **[docs/project_info/BUILD.md](docs/project_info/BUILD.md)** - Инструкции по сборке
- **[docs/project_info/SECRET_KEY.md](docs/project_info/SECRET_KEY.md)** - Генерация SECRET_KEY
- **[docs/lessons/i18n/README.md](docs/lessons/i18n/README.md)** - Локализация приложения
- **[backup_tools/README.md](backup_tools/README.md)** - Инструменты резервного копирования

---

**Версия документа:** 4.0.7  
**Последнее обновление:** 14 октября 2025  
**Статус:** Production Ready ✅

**⚠️ ВАЖНО**: Перед началом работы обязательно прочитайте [SECURITY.md](SECURITY.md) и настройте `.env` + `config.json`!

