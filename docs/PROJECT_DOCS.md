# 📚 Документация проекта VPN Server Manager

> Полная документация: архитектура, структура, правила разработки

---



<!-- ====================================================================== -->
<!-- РАЗДЕЛ: PROJECT_DOCUMENTATION.md -->
<!-- ====================================================================== -->

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

### v4.0.7 (14 октября 2025)
- 🚀 **КРИТИЧЕСКОЕ: Исправлена производительность**: Добавлен многопоточный режим Flask (threaded=True)
  - Переход на страницу мониторинга теперь **мгновенный** (было 40 секунд задержки)
  - Приложение может обрабатывать несколько запросов одновременно
  - Web режим: `app.run(..., threaded=True)` в `run.py`
  - Desktop режим: `make_server(..., threaded=True)` с переходом на werkzeug в `desktop/window.py`
- ⚡ **Ускорена проверка мониторинга**: Таймауты 10/8 секунд (вместо 30/15)
  - Проверка установки: 10-18 секунд вместо 40-45
  - Добавлен параметр `connection_timeout` в SSH сервис
- ⏳ **Исправлен индикатор загрузки**: Теперь показывается сразу при открытии мониторинга
- 🔒 **КРИТИЧЕСКОЕ обновление безопасности**: Удалены конфиденциальные файлы (.env, config.json, *.enc) из всей истории Git
- 🔐 **Новый SECRET_KEY**: Сгенерирован безопасный ключ шифрования
- 📝 **config.json теперь локальный**: Добавлен в .gitignore, создан config.json.example как шаблон
- 🛡️ **Документация по безопасности**: Полное руководство в SECURITY.md
- ⚙️ **build_macos.py исправлен**: DMG больше не содержит конфиденциальные файлы
- 📋 **Обновлены шаблоны**: env.example и config.json.example с комментариями

### v4.0.5 (12 октября 2025)
- 🐛 **Функция "Сохранить как PNG"**: Полностью реализована функция сохранения статистики сервера в PNG
- 🔐 **PIN аутентификация**: Исправлено отображение ошибки при неправильном PIN
- 🌐 **SSH подключение**: Добавлена поддержка нестандартных SSH портов (22542)
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

- ✅ **Многопоточность Flask**: Обработка нескольких запросов одновременно (threaded=True)
- ✅ **Мгновенная навигация**: Никогда не блокируется другими запросами
- ✅ **Быстрые проверки**: Оптимизированные таймауты (10/8 сек для проверки установки)
- ✅ **SSH Connection Pooling**: Повторное использование SSH соединений
- ✅ **Rate Limiting**: Защита от перегрузки API (10 req/мин)
- ✅ **Graceful Shutdown**: Закрытие всех SSH соединений при выходе
- ✅ **Error Handling**: Автоматическая остановка при потере соединения
- ✅ **System Stats**: Эндпоинт статистики системы мониторинга
- ✅ **Health Check**: Эндпоинт проверки работоспособности

### Технические детали

- **Threading**: `threaded=True` в run.py и desktop/window.py для многопоточности
- **WSGI**: `werkzeug.serving.make_server('127.0.0.1', 0, app, threaded=True)` в desktop режиме
- **Timeouts**: Настраиваемые таймауты (10 сек для быстрых операций, 30 сек для обычных)
- **Cookie**: `SESSION_COOKIE_NAME = 'vpn_manager_session_clean'`
- **Shutdown**: Эндпоинт `/shutdown` + обработчик `on_closing`
- **Exit**: `logout()` → `session.clear()` → `window.destroy()` → `os._exit(0)`
- **Session**: `private_mode=True`, отключен `SESSION_TYPE='filesystem'`
- **SSH Pool**: `SSHService._connection_pool` с `_pool_lock`
- **Rate Limit**: `RateLimiter(max_requests=10, time_window=60)`

### Преимущества

- ✅ **Мгновенная навигация**: Многопоточность предотвращает блокировку запросов
- ✅ **Быстрые проверки**: Оптимизированные таймауты для разных операций
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

- **v4.0.7** (14.10.2025) - 🔒 **КРИТИЧЕСКОЕ обновление безопасности** + 🚀 **Исправления производительности**
- **v4.0.5** (12.10.2025) - Исправления PNG сохранения, PIN ошибок, SSH портов, переводы
- **v4.0.4** (12.10.2025) - Поддержка Windows, Docker документация, Git конфигурация
- **v4.0.3** (12.10.2025) - Централизованная версия + критические исправления для macOS frozen режима
- **v4.0.2** (12.10.2025) - Multi-App Support, динамические порты, изолированные сессии
- **v4.0.1** (11.10.2025) - Исправление PIN аутентификации
- **v4.0.0** (15.01.2025) - Полная реструктуризация архитектуры

### 🔧 Ключевые исправления v4.0.7

#### Производительность (КРИТИЧЕСКОЕ!)
- ✅ **Многопоточность Flask**: `threaded=True` в run.py и desktop/window.py
- ✅ **Мгновенная навигация**: Переход на мониторинг за < 1 секунду (было 40 секунд)
- ✅ **Быстрые проверки**: Таймауты 10/8 секунд для проверки установки
- ✅ **Динамические таймауты**: `connection_timeout` параметр в SSH сервисе
- ✅ **Werkzeug в desktop**: Переход с wsgiref на werkzeug для многопоточности
- ✅ **Индикатор загрузки**: Показывается сразу при открытии страницы

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
- ✅ Поддержка нестандартных SSH портов (22542)
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
**Последнее обновление:** 14 октября 2025 (вечер)  
**Статус:** Production Ready ✅

**🚀 ИСПРАВЛЕНО**: Критическая проблема с производительностью - добавлена многопоточность Flask!  
**⚠️ ВАЖНО**: Перед началом работы обязательно прочитайте [SECURITY.md](SECURITY.md) и настройте `.env` + `config.json`!



<!-- ====================================================================== -->
<!-- РАЗДЕЛ: Структура.md -->
<!-- ====================================================================== -->

# Структура проекта VPN Server Manager v4.0.9

## 📋 Обзор проекта

**VPN Server Manager** - современное приложение для управления VPN-серверами с модульной архитектурой, шифрованием данных и поддержкой нескольких платформ (macOS, Windows, Linux, Docker).

**Стек технологий:**
- Backend: Flask (Python 3.8+)
- Frontend: HTML5, Bootstrap 5, JavaScript
- Desktop UI: PyWebView (кроссплатформенная обертка)
- Шифрование: Fernet (AES-128 + HMAC-SHA256)
- SSH: Paramiko с пулом соединений
- i18n: Flask-Babel (русский, английский, китайский)
- Тестирование: Pytest с coverage
- Сборка: PyInstaller, Docker

---

## 📁 Структура директорий

```
vpn-server-manager/
├── app/                          # Основное Flask приложение
│   ├── __init__.py              # Application Factory
│   ├── config.py                # Конфигурация приложения
│   ├── exceptions.py            # Кастомные исключения
│   ├── models/                  # Модели данных
│   │   ├── __init__.py
│   │   ├── server.py           # Модель Server (dataclass)
│   │   ├── server_connection.py # Модель ServerConnection
│   │   └── server_stats.py     # Модель ServerStats
│   ├── routes/                  # Маршруты и API endpoints
│   │   ├── __init__.py
│   │   ├── main.py             # Основные веб-маршруты
│   │   ├── api.py              # RESTful API endpoints
│   │   ├── pin.py              # PIN аутентификация
│   │   └── vendor.py           # Vendor файлы (bootstrap, icons)
│   ├── services/                # Бизнес-логика (Service Layer)
│   │   ├── __init__.py         # ServiceRegistry
│   │   ├── ssh_service.py      # SSH/SFTP операции
│   │   ├── crypto_service.py   # Шифрование/дешифрование
│   │   ├── data_manager_service.py # Управление данными
│   │   └── api_service.py      # Внешние API (IP check, location)
│   └── utils/                   # Утилиты
│       ├── __init__.py
│       ├── decorators.py       # Декораторы (@require_auth, @rate_limit, etc)
│       ├── validators.py       # Валидация данных
│       └── rate_limiter.py     # Rate limiting (Token Bucket)
├── desktop/                     # PyWebView desktop приложение
│   └── window.py               # Управление desktop окном
├── templates/                   # Jinja2 HTML шаблоны
│   ├── layout.html             # Базовый layout
│   ├── index.html              # Главная страница
│   ├── index_locked.html       # PIN-аутентификация
│   ├── add_server.html         # Форма добавления сервера
│   ├── edit_server.html        # Форма редактирования
│   ├── monitoring.html         # Dashboard мониторинга
│   ├── settings.html           # Настройки
│   ├── help.html               # Справка
│   ├── cheatsheet.html         # Шпаргалка (NGINX, Docker, Systemd)
│   └── ...                     # Другие шаблоны
├── static/                      # Статические файлы
│   ├── css/                    # Стили
│   │   ├── style.css          # Основные стили
│   │   └── monitoring.css     # Стили мониторинга
│   ├── js/                     # JavaScript
│   │   └── bootstrap.bundle.min.js
│   └── images/                 # Изображения
├── translations/                # Переводы (i18n)
│   ├── ru/                     # Русский
│   ├── en/                     # Английский
│   └── zh/                     # Китайский
├── tests/                       # Тесты
│   ├── conftest.py             # Pytest конфигурация и фикстуры
│   ├── test_routes/            # Тесты маршрутов
│   └── test_services/          # Тесты сервисов
├── backup_tools/                # Утилиты резервного копирования
├── docs/                        # Документация
├── tools/                       # Инструменты разработки
│   ├── auto_translate_po.py    # Автоматический перевод
│   └── ...
├── run.py                       # Главный запускатель (web/desktop)
├── run_desktop.py               # Прямой запуск desktop
├── setup.py                     # Метаданные пакета
├── requirements.txt             # Python зависимости
├── Makefile                     # Команды сборки
├── Dockerfile                   # Docker образ
├── docker-compose.yml           # Docker Compose
├── .env                         # Переменные окружения (не в Git)
├── config.json                  # Конфигурация приложения (не в Git)
├── config.json.example          # Шаблон конфигурации
└── env.example                  # Шаблон .env
```

---

## 🔑 Основные файлы и их назначение

### Точки входа

#### **run.py** - Главный запускатель приложения
```python
# Основные возможности:
def main():
    # 1. Парсинг аргументов командной строки
    parser = argparse.ArgumentParser()
    parser.add_argument('--desktop', action='store_true')
    parser.add_argument('--debug', action='store_true')

    # 2. Поиск свободного порта для multi-instance
    port = find_free_port(start_port=5000, max_attempts=10)

    # 3. Создание Flask приложения через Application Factory
    app = create_app('development' if debug else 'production')

    # 4. Graceful shutdown с очисткой SSH соединений
    def signal_handler(sig, frame):
        ssh_service = registry.get('ssh')
        ssh_service.cleanup_connections()
        sys.exit(0)

    # 5. Запуск в web или desktop режиме
    if desktop:
        from desktop.window import start_desktop_app
        start_desktop_app(app, port)
    else:
        app.run(host='127.0.0.1', port=port, threaded=True)
```

**Ключевые функции:**
- `find_free_port()` - поиск свободного порта (5000-5009)
- `signal_handler()` - обработка SIGINT/SIGTERM для graceful shutdown
- `threaded=True` - многопоточный режим Flask (критично для производительности)

---

### Application Factory

#### **app/__init__.py** - Фабрика приложения
```python
def create_app(config_name='production'):
    """
    Application Factory Pattern для создания Flask приложения
    """
    # 1. Инициализация Flask
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    # 2. Загрузка конфигурации
    app.config.from_object(config_by_name[config_name])

    # 3. Управление пользовательским config.json (frozen mode)
    manage_user_config(app)

    # 4. Инициализация Babel для i18n
    babel = Babel(app, locale_selector=get_locale)

    # 5. Настройка логирования
    setup_logging(app)

    # 6. Регистрация сервисов в Service Registry
    register_services(app)

    # 7. Регистрация blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(pin_bp)

    # 8. Регистрация обработчиков ошибок
    register_error_handlers(app)

    # 9. Настройка сессий
    app.config['SESSION_COOKIE_NAME'] = 'vpn_manager_session_clean'

    # 10. Загрузка app_info из config.json
    load_app_info(app)

    return app
```

**Ключевые функции:**
- `get_locale()` - определение языка по сессии/браузеру
- `manage_user_config()` - копирование config.json в APP_DATA_DIR (frozen mode)
- `register_services()` - инициализация Service Registry (DI контейнер)
- `load_app_info()` - загрузка версии и метаданных из config.json

---

### Конфигурация

#### **app/config.py** - Система конфигурации
```python
def get_app_data_dir():
    """
    Возвращает путь к данным приложения с учетом платформы
    """
    is_frozen = getattr(sys, 'frozen', False)
    app_name = "VPNServerManager-Clean"

    if is_frozen:
        if sys.platform == 'darwin':  # macOS
            return os.path.join(
                os.path.expanduser("~"),
                "Library", "Application Support",
                app_name
            )
        elif sys.platform == 'win32':  # Windows
            return os.path.join(
                os.getenv('APPDATA'),
                app_name
            )
        else:  # Linux
            return os.path.join(
                os.path.expanduser("~"),
                ".local", "share",
                app_name
            )
    else:
        # Development mode - корень проекта
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Config:
    """Базовая конфигурация"""
    SECRET_KEY = os.getenv('SECRET_KEY')
    APP_VERSION = os.getenv('APP_VERSION', '4.0.9')
    APP_DATA_DIR = get_app_data_dir()

    # Пути к данным
    DATA_DIR = os.path.join(APP_DATA_DIR, 'data')
    SERVERS_FILE = 'servers.json.enc'

    # API URLs
    IP_CHECK_API = 'https://ipinfo.io/{ip}/json'

    # Babel i18n
    BABEL_DEFAULT_LOCALE = 'ru'
    BABEL_SUPPORTED_LOCALES = ['ru', 'en', 'zh']
```

**Ключевые особенности:**
- Автоматическое создание `.env` в frozen mode с новым SECRET_KEY
- Платформо-зависимые пути к данным
- Конфигурационные классы: Development, Production, Testing

---

## 🔧 Service Layer (Бизнес-логика)

### **app/services/__init__.py** - Service Registry (DI)

```python
class ServiceRegistry:
    """
    Dependency Injection контейнер для управления сервисами
    """
    def __init__(self):
        self._services = {}

    def register(self, name: str, service):
        """Регистрация сервиса"""
        self._services[name] = service

    def get(self, name: str):
        """Получение сервиса"""
        return self._services.get(name)

# Глобальный реестр сервисов
registry = ServiceRegistry()
```

**Использование:**
```python
# Регистрация
registry.register('ssh', SSHService())
registry.register('crypto', CryptoService())

# Получение
ssh_service = registry.get('ssh')
ssh_service.execute_command(server_id, 'ls -la')
```

---

### **app/services/ssh_service.py** - SSH/SFTP сервис (44 KB)

**Основные возможности:**

#### 1. Connection Pooling (пул соединений)
```python
class SSHService:
    def __init__(self):
        self.connections = {}  # {server_id: {'client': SSHClient, 'last_used': timestamp}}
        self.connection_locks = {}  # Thread-safe locks
        self.pool_lock = threading.Lock()

    def get_or_create_connection(self, server_id: str, server: Server):
        """
        Получает существующее соединение или создает новое
        """
        with self.pool_lock:
            if server_id in self.connections:
                conn_info = self.connections[server_id]
                # Проверяем активность соединения
                if self._is_connection_alive(conn_info['client']):
                    conn_info['last_used'] = time.time()
                    return conn_info['client']
                else:
                    # Переподключаемся
                    self._close_connection(server_id)

            # Создаем новое соединение
            client = self._create_ssh_client(server)
            self.connections[server_id] = {
                'client': client,
                'created_at': time.time(),
                'last_used': time.time()
            }
            return client

    def _is_connection_alive(self, client: paramiko.SSHClient):
        """Проверка активности SSH соединения"""
        try:
            transport = client.get_transport()
            if transport and transport.is_active():
                transport.send_ignore()  # Keepalive ping
                return True
        except:
            pass
        return False
```

#### 2. Выполнение SSH команд
```python
def execute_command(self, server_id: str, command: str, timeout: int = 30):
    """
    Выполняет SSH команду на удаленном сервере
    """
    server = self._get_server(server_id)
    client = self.get_or_create_connection(server_id, server)

    try:
        stdin, stdout, stderr = client.exec_command(
            command,
            timeout=timeout,
            get_pty=True  # Псевдо-терминал для sudo
        )

        # Читаем вывод
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        exit_code = stdout.channel.recv_exit_status()

        return {
            'output': output,
            'error': error,
            'exit_code': exit_code,
            'success': exit_code == 0
        }
    except socket.timeout:
        raise SSHConnectionError(f"Command timeout after {timeout}s")
    except Exception as e:
        raise SSHConnectionError(f"Command execution failed: {e}")
```

#### 3. SFTP операции
```python
def upload_file(self, server_id: str, local_path: str, remote_path: str):
    """Загрузка файла на сервер через SFTP"""
    client = self.get_or_create_connection(server_id, server)
    sftp = client.open_sftp()
    try:
        sftp.put(local_path, remote_path)
        sftp.chmod(remote_path, 0o644)
    finally:
        sftp.close()

def download_file(self, server_id: str, remote_path: str, local_path: str):
    """Скачивание файла с сервера"""
    client = self.get_or_create_connection(server_id, server)
    sftp = client.open_sftp()
    try:
        sftp.get(remote_path, local_path)
    finally:
        sftp.close()
```

#### 4. Мониторинг
```python
def get_network_stats(self, server_id: str):
    """Получение сетевой статистики"""
    result = self.execute_command(server_id, """
        cat /proc/net/dev | grep -v lo | awk 'NR>2 {
            print $1, $2, $10
        }'
    """)
    # Парсинг и форматирование данных
    return parsed_stats

def check_firewall_status(self, server_id: str):
    """Проверка статуса firewall (UFW/iptables)"""
    # Проверяем UFW
    ufw_result = self.execute_command(server_id, 'sudo ufw status')
    if 'Status: active' in ufw_result['output']:
        return self._parse_ufw_rules(ufw_result['output'])

    # Fallback на iptables
    iptables_result = self.execute_command(server_id, 'sudo iptables -L -n')
    return self._parse_iptables_rules(iptables_result['output'])

def get_service_status(self, server_id: str, service_name: str):
    """Проверка статуса systemd сервиса"""
    result = self.execute_command(
        server_id,
        f'systemctl is-active {service_name}'
    )
    return result['output'].strip() == 'active'
```

#### 5. Cleanup
```python
def cleanup_connections(self):
    """Закрытие всех SSH соединений (graceful shutdown)"""
    with self.pool_lock:
        for server_id in list(self.connections.keys()):
            self._close_connection(server_id)
        self.connections.clear()
        self.connection_locks.clear()

def cleanup_idle_connections(self, max_idle_time: int = 300):
    """Очистка неактивных соединений (5 минут)"""
    with self.pool_lock:
        current_time = time.time()
        for server_id, conn_info in list(self.connections.items()):
            if current_time - conn_info['last_used'] > max_idle_time:
                self._close_connection(server_id)
```

---

### **app/services/crypto_service.py** - Сервис шифрования

```python
class CryptoService:
    def __init__(self):
        self._fernet = None
        self._key = None

    def set_key(self, key: str):
        """Установка ключа шифрования"""
        if isinstance(key, str):
            key = key.encode()
        self._key = key
        self._fernet = Fernet(key)

    def encrypt_string(self, data: str) -> str:
        """Шифрование строки"""
        if not self._fernet:
            raise CryptoError("Encryption key not set")

        encrypted = self._fernet.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_string(self, encrypted_data: str) -> str:
        """Расшифровка строки"""
        if not self._fernet:
            raise CryptoError("Encryption key not set")

        try:
            decoded = base64.b64decode(encrypted_data.encode())
            decrypted = self._fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            raise CryptoError(f"Decryption failed: {e}")

    def encrypt_file(self, input_path: str, output_path: str):
        """Шифрование файла"""
        with open(input_path, 'rb') as f:
            data = f.read()

        encrypted = self._fernet.encrypt(data)

        with open(output_path, 'wb') as f:
            f.write(encrypted)

    def decrypt_file(self, input_path: str, output_path: str):
        """Расшифровка файла"""
        with open(input_path, 'rb') as f:
            encrypted = f.read()

        decrypted = self._fernet.decrypt(encrypted)

        with open(output_path, 'wb') as f:
            f.write(decrypted)

    @staticmethod
    def generate_key() -> str:
        """Генерация нового ключа Fernet"""
        return Fernet.generate_key().decode()
```

**Использование:**
```python
crypto = registry.get('crypto')
crypto.set_key(app.config['SECRET_KEY'])

# Шифрование данных сервера
encrypted_password = crypto.encrypt_string(server.password)

# Шифрование файла
crypto.encrypt_file('servers.json', 'servers.json.enc')
```

---

### **app/services/data_manager_service.py** - Управление данными

```python
class DataManagerService:
    def __init__(self, secret_key: str, app_data_dir: str):
        self.crypto = CryptoService()
        self.crypto.set_key(secret_key)
        self.app_data_dir = app_data_dir
        self.data_dir = os.path.join(app_data_dir, 'data')
        os.makedirs(self.data_dir, exist_ok=True)

    def load_servers(self, file_path: str = None) -> List[Server]:
        """
        Загрузка серверов из файла (зашифрованного или обычного)
        """
        if not file_path:
            file_path = self._get_active_data_file()

        if not os.path.exists(file_path):
            return []

        # Определяем тип файла по расширению
        if file_path.endswith('.enc'):
            return self._load_encrypted_servers(file_path)
        else:
            return self._load_plain_servers(file_path)

    def _load_encrypted_servers(self, file_path: str) -> List[Server]:
        """Загрузка из зашифрованного файла"""
        try:
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = self.crypto._fernet.decrypt(encrypted_data)
            data = json.loads(decrypted_data.decode())

            return [Server.from_dict(s) for s in data.get('servers', [])]
        except Exception as e:
            raise CryptoError(f"Failed to decrypt file: {e}")

    def save_servers(self, servers: List[Server], file_path: str = None):
        """
        Сохранение серверов в файл (зашифрованный или обычный)
        """
        if not file_path:
            file_path = self._get_active_data_file()

        data = {
            'servers': [s.to_dict() for s in servers],
            'version': '4.0.9',
            'timestamp': datetime.now().isoformat()
        }

        if file_path.endswith('.enc'):
            self._save_encrypted_servers(data, file_path)
        else:
            self._save_plain_servers(data, file_path)

    def _save_encrypted_servers(self, data: dict, file_path: str):
        """Сохранение в зашифрованный файл"""
        json_data = json.dumps(data, indent=2, ensure_ascii=False)
        encrypted = self.crypto._fernet.encrypt(json_data.encode())

        with open(file_path, 'wb') as f:
            f.write(encrypted)

    def import_data(self, source_path: str, target_file: str = None):
        """
        Импорт данных из файла (.enc, .json, .zip)
        """
        if source_path.endswith('.zip'):
            return self._import_from_zip(source_path, target_file)
        elif source_path.endswith('.enc'):
            return self._import_encrypted(source_path, target_file)
        else:
            return self._import_plain(source_path, target_file)

    def export_data(self, servers: List[Server], export_path: str, encrypt: bool = True):
        """
        Экспорт данных в файл
        """
        if encrypt:
            export_path = export_path.replace('.json', '.enc')
            self.save_servers(servers, export_path)
        else:
            self._save_plain_servers({
                'servers': [s.to_dict() for s in servers],
                'version': '4.0.9',
                'timestamp': datetime.now().isoformat()
            }, export_path)

    def create_png_snapshot(self, server: Server, stats: dict, output_path: str):
        """
        Создание PNG снимка статистики сервера
        """
        # HTML рендеринг статистики с использованием html2canvas
        # (реализовано через JavaScript на клиенте)
        pass
```

---

## 🌐 Routes (API Endpoints)

### **app/routes/api.py** - RESTful API (68 KB)

**Основные группы endpoints:**

#### 1. Управление серверами
```python
@api_bp.route('/api/servers', methods=['GET'])
@require_auth
def get_servers():
    """Получить список всех серверов"""
    data_manager = registry.get('data_manager')
    servers = data_manager.load_servers()
    return jsonify([s.to_dict() for s in servers])

@api_bp.route('/api/servers', methods=['POST'])
@require_auth
@validate_json(['name', 'hostname', 'username'])
def create_server():
    """Создать новый сервер"""
    data = request.get_json()
    server = Server.from_dict(data)

    data_manager = registry.get('data_manager')
    servers = data_manager.load_servers()
    servers.append(server)
    data_manager.save_servers(servers)

    return jsonify(server.to_dict()), 201

@api_bp.route('/api/servers/<server_id>', methods=['PUT'])
@require_auth
@validate_json(['name', 'hostname'])
def update_server(server_id):
    """Обновить сервер"""
    # Реализация обновления
    pass

@api_bp.route('/api/servers/<server_id>', methods=['DELETE'])
@require_auth
def delete_server(server_id):
    """Удалить сервер"""
    # Реализация удаления
    pass
```

#### 2. SSH операции
```python
@api_bp.route('/api/servers/<server_id>/test', methods=['POST'])
@require_auth
@rate_limit(max_requests=5, window=60)
def test_connection(server_id):
    """Тест SSH подключения"""
    ssh_service = registry.get('ssh')

    try:
        result = ssh_service.execute_command(server_id, 'echo "OK"')
        return jsonify({
            'success': True,
            'message': 'Connection successful',
            'output': result['output']
        })
    except SSHConnectionError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 503

@api_bp.route('/api/servers/<server_id>/status', methods=['GET'])
@require_auth
def get_server_status(server_id):
    """Получить статус сервера"""
    ssh_service = registry.get('ssh')

    try:
        # Проверка доступности
        result = ssh_service.execute_command(server_id, 'uptime')

        return jsonify({
            'status': 'connected',
            'uptime': result['output']
        })
    except:
        return jsonify({'status': 'disconnected'})
```

#### 3. Мониторинг
```python
@api_bp.route('/api/monitoring/network/<server_id>', methods=['GET'])
@require_auth
@rate_limit(max_requests=10, window=60)
def get_network_stats(server_id):
    """Получить сетевую статистику"""
    ssh_service = registry.get('ssh')
    stats = ssh_service.get_network_stats(server_id)
    return jsonify(stats)

@api_bp.route('/api/monitoring/firewall/<server_id>', methods=['GET'])
@require_auth
def get_firewall_status(server_id):
    """Получить статус firewall"""
    ssh_service = registry.get('ssh')
    status = ssh_service.check_firewall_status(server_id)
    return jsonify(status)

@api_bp.route('/api/monitoring/services/<server_id>', methods=['GET'])
@require_auth
def get_services_status(server_id):
    """Получить статус сервисов"""
    services = request.args.getlist('service')
    ssh_service = registry.get('ssh')

    results = {}
    for service in services:
        results[service] = ssh_service.get_service_status(server_id, service)

    return jsonify(results)

@api_bp.route('/api/monitoring/security/<server_id>', methods=['GET'])
@require_auth
def get_security_events(server_id):
    """Получить события безопасности (auth.log)"""
    ssh_service = registry.get('ssh')
    result = ssh_service.execute_command(
        server_id,
        "sudo tail -100 /var/log/auth.log | grep -i 'failed\\|accepted'"
    )
    return jsonify({'events': result['output'].split('\n')})
```

#### 4. EventSource (Server-Sent Events)
```python
@api_bp.route('/api/monitoring/install/<server_id>')
@require_auth
def install_monitoring_stream(server_id):
    """
    Установка monitoring с прогрессом через EventSource
    """
    def generate():
        ssh_service = registry.get('ssh')

        # Шаг 1: Проверка зависимостей
        yield f"data: {json.dumps({'step': 1, 'message': 'Checking dependencies...'})}\n\n"

        # Шаг 2: Установка пакетов
        yield f"data: {json.dumps({'step': 2, 'message': 'Installing packages...'})}\n\n"
        result = ssh_service.execute_command(
            server_id,
            'sudo apt-get update && sudo apt-get install -y iftop htop'
        )

        # Шаг 3: Конфигурация
        yield f"data: {json.dumps({'step': 3, 'message': 'Configuring...'})}\n\n"

        # Завершение
        yield f"data: {json.dumps({'step': 4, 'message': 'Done!', 'success': True})}\n\n"

    return Response(generate(), mimetype='text/event-stream')
```

#### 5. Утилиты
```python
@api_bp.route('/api/ip-check', methods=['POST'])
@require_auth
@rate_limit(max_requests=20, window=60)
def check_ip():
    """Проверка IP адреса"""
    data = request.get_json()
    ip = data.get('ip')

    api_service = registry.get('api')
    info = api_service.check_ip(ip)

    return jsonify(info)

@api_bp.route('/api/dns-test', methods=['POST'])
@require_auth
def dns_leak_test():
    """DNS leak test"""
    # Реализация DNS теста
    pass

@api_bp.route('/api/snapshot/save', methods=['POST'])
@require_auth
def save_snapshot():
    """Сохранение PNG снимка статистики"""
    data = request.get_json()
    image_data = data.get('image')  # Base64

    # Декодирование и сохранение в Downloads
    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    filename = f"vpn_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(downloads_dir, filename)

    # Декодирование base64
    img_bytes = base64.b64decode(image_data.split(',')[1])
    with open(filepath, 'wb') as f:
        f.write(img_bytes)

    return jsonify({
        'success': True,
        'path': filepath
    })
```

---

## 🎨 Templates (Jinja2)

### **templates/layout.html** - Базовый layout

```html
<!DOCTYPE html>
<html lang="{{ get_locale() }}">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}VPN Server Manager{% endblock %}</title>
    <link href="/static/css/bootstrap.min.css" rel="stylesheet">
    <link href="/static/css/style.css" rel="stylesheet">
</head>
<body>
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">
                VPN Manager v{{ app_info.version }}
            </a>

            <!-- Language Selector -->
            <ul class="navbar-nav">
                <li class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
                        {{ _('Language') }}
                    </a>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="?lang=ru">Русский</a></li>
                        <li><a class="dropdown-item" href="?lang=en">English</a></li>
                        <li><a class="dropdown-item" href="?lang=zh">中文</a></li>
                    </ul>
                </li>
            </ul>
        </div>
    </nav>

    <!-- Flash Messages -->
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }} alert-dismissible">
                    {{ message }}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <!-- Content -->
    <div class="container mt-4">
        {% block content %}{% endblock %}
    </div>

    <!-- Footer -->
    <footer class="footer mt-5 py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">
                VPN Server Manager v{{ app_info.version }} |
                {{ app_info.developer }} |
                {{ server_info.url }}
            </span>
        </div>
    </footer>

    <script src="/static/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

---

## 🛡️ Utilities (Декораторы)

### **app/utils/decorators.py**

```python
def require_auth(f):
    """Проверка аутентификации по PIN"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('main.index_locked'))
        return f(*args, **kwargs)
    return decorated_function

def require_pin(f):
    """Проверка PIN для критичных операций"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.get_json() if request.is_json else request.form
        pin = data.get('pin')

        if not pin or pin != current_app.config['DEFAULT_PIN']:
            return jsonify({'error': 'Invalid PIN'}), 401

        return f(*args, **kwargs)
    return decorated_function

def rate_limit(max_requests: int = 10, window: int = 60):
    """Rate limiting (Token Bucket)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from .rate_limiter import RateLimiter

            limiter = RateLimiter(max_requests, window)
            client_id = request.remote_addr

            if not limiter.allow_request(client_id):
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': window
                }), 429

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_json(required_fields: list):
    """Валидация JSON данных"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400

            data = request.get_json()
            missing = [field for field in required_fields if field not in data]

            if missing:
                return jsonify({
                    'error': f'Missing required fields: {", ".join(missing)}'
                }), 400

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def handle_errors(f):
    """Обработка ошибок"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AppException as e:
            if request.is_json:
                return jsonify({'error': str(e)}), e.status_code
            flash(str(e), 'error')
            return redirect(url_for('main.index'))
        except Exception as e:
            current_app.logger.error(f"Unhandled error: {e}")
            if request.is_json:
                return jsonify({'error': 'Internal server error'}), 500
            flash('Произошла ошибка', 'error')
            return redirect(url_for('main.index'))
    return decorated_function
```

---

## 📊 Models (Модели данных)

### **app/models/server.py**

```python
from dataclasses import dataclass, field
from typing import Optional
import uuid
from datetime import datetime

@dataclass
class Server:
    """Модель VPN сервера"""
    name: str
    hostname: str
    username: str
    password: Optional[str] = None
    ssh_key_path: Optional[str] = None
    ssh_port: int = 22
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = 'unknown'
    notes: str = ''

    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {
            'id': self.id,
            'name': self.name,
            'hostname': self.hostname,
            'username': self.username,
            'password': self.password,
            'ssh_key_path': self.ssh_key_path,
            'ssh_port': self.ssh_port,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'status': self.status,
            'notes': self.notes
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Server':
        """Создание из словаря"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data['name'],
            hostname=data['hostname'],
            username=data['username'],
            password=data.get('password'),
            ssh_key_path=data.get('ssh_key_path'),
            ssh_port=data.get('ssh_port', 22),
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
            status=data.get('status', 'unknown'),
            notes=data.get('notes', '')
        )

    def validate(self) -> bool:
        """Валидация данных"""
        if not self.name or not self.hostname or not self.username:
            return False
        if not self.password and not self.ssh_key_path:
            return False
        if self.ssh_port < 1 or self.ssh_port > 65535:
            return False
        return True
```

---

## 🔐 Безопасность

### Ключевые механизмы безопасности:

1. **PIN-аутентификация**
   - Сессионная аутентификация
   - PIN хранится в `.env` или `config.json`
   - Проверка через декоратор `@require_auth`

2. **Шифрование данных**
   - Fernet (AES-128 + HMAC-SHA256)
   - Шифрование паролей серверов
   - Шифрование файлов данных (`.enc`)

3. **Rate Limiting**
   - Token Bucket алгоритм
   - Лимиты на API endpoints
   - Защита от brute-force

4. **Валидация данных**
   - JSON Schema валидация
   - Санитизация входных данных
   - Защита от SQL injection (не используется SQL)

5. **CSRF защита**
   - Flask-WTF CSRF токены
   - Проверка Origin header

---

## 🧪 Тестирование

### **tests/conftest.py** - Pytest fixtures

```python
import pytest
from app import create_app
from app.services import registry

@pytest.fixture
def app():
    """Создание тестового приложения"""
    app = create_app('testing')
    return app

@pytest.fixture
def client(app):
    """Flask test client"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Flask CLI runner"""
    return app.test_cli_runner()

@pytest.fixture
def authenticated_client(client):
    """Аутентифицированный клиент"""
    with client.session_transaction() as sess:
        sess['authenticated'] = True
    return client
```

### Пример теста:

```python
def test_get_servers(authenticated_client):
    """Тест получения списка серверов"""
    response = authenticated_client.get('/api/servers')
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert isinstance(data, list)
```

---

## 🐳 Docker

### **Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY . .

# Переменные окружения
ENV FLASK_APP=run.py
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python", "run.py"]
```

### **docker-compose.yml**

```yaml
version: '3.8'

services:
  vpn-manager:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env
    environment:
      - FLASK_ENV=production
    restart: unless-stopped
```

---

## 📝 Основные workflow

### 1. Добавление нового сервера

```
User → /add_server (form) → POST /api/servers
  → validate_json(['name', 'hostname', 'username'])
  → Server.from_dict(data)
  → DataManagerService.save_servers()
  → CryptoService.encrypt_file()
  → Response 201
```

### 2. Тест SSH подключения

```
User → Click "Test" → POST /api/servers/{id}/test
  → SSHService.get_or_create_connection()
  → paramiko.SSHClient.connect()
  → execute_command('echo OK')
  → Response {success: true}
```

### 3. Мониторинг сервера

```
User → /monitoring → GET /api/monitoring/network/{id}
  → SSHService.execute_command('cat /proc/net/dev')
  → Parse output
  → Response {interfaces: [...]}
```

### 4. Экспорт данных в PNG

```
User → Click "Save as PNG" → JavaScript html2canvas
  → Canvas to Base64
  → POST /api/snapshot/save {image: base64}
  → base64.b64decode()
  → Save to ~/Downloads/vpn_stats_{timestamp}.png
  → Response {success: true, path: ...}
```

---

## 🚀 Производительность

### Критические оптимизации:

1. **Multi-threading Flask**
   ```python
   app.run(threaded=True)  # Обработка множественных запросов
   ```

2. **SSH Connection Pooling**
   - Переиспользование соединений
   - Проверка активности (keepalive ping)
   - Автоматическая очистка idle соединений

3. **Lazy Loading**
   - Сервисы инициализируются при первом обращении
   - Данные загружаются по требованию

4. **Caching**
   - Декоратор `@cache_response`
   - In-memory кеш для частых запросов

---

## 📚 Дополнительные материалы

- **Архитектурные правила**: `ArchitecturalRules.md`
- **Документация проекта**: `PROJECT_DOCUMENTATION.md`
- **Руководство по миграции**: `MIGRATION_GUIDE.md`
- **Безопасность**: `SECURITY.md`, `SECURITY_AUDIT_REPORT.md`
- **Релиз гайд**: `docs/release_guide.md`

---

## 🎯 Заключение

VPN Server Manager v4.0.9 - это полнофункциональное приложение с:
- Модульной архитектурой (Application Factory, Service Layer, Blueprints)
- Высокой производительностью (multi-threading, connection pooling)
- Надежной безопасностью (шифрование, PIN, rate limiting)
- Кроссплатформенностью (macOS, Windows, Linux, Docker)
- Современными практиками разработки (DI, decorators, type hints)
- Comprehensive testing (pytest, coverage)
- Полной интернационализацией (ru, en, zh)

Приложение готово к production использованию и активной разработке новых функций.


<!-- ====================================================================== -->
<!-- РАЗДЕЛ: ArchitecturalRules.md -->
<!-- ====================================================================== -->

# Архитектурные правила для Flask-приложения v4.0.7

## Контекст проекта

**VPN Server Manager** - Flask-приложение с desktop GUI (pywebview), поддержкой интернационализации, SSH/SFTP функциональностью и криптографией.

**v4.0.7 (13 октября 2025)**: 
- ✅ **БЕЗОПАСНОСТЬ**: Конфиденциальные файлы (.env, config.json) исключены из Git
- ✅ config.json теперь локальный файл (шаблон: config.json.example)
- ✅ Исправлена сборка DMG - не включает секреты
- ✅ Полная документация по безопасности (SECURITY.md)

**v4.0.3**: 
- ✅ Централизованное управление версией из `config.json`
- ✅ Multi-App Support (параллельный запуск)
- ✅ Модульная архитектура (Application Factory, Service Layer)
- ✅ DataManagerService для управления данными

## Структура проекта (v4.0.3)

```
VPNserverManage-Clean/
├── run.py                        # Точка входа (web/desktop режимы)
├── config.json                   # 🎯 Конфигурация (version: 4.0.7) - ЛОКАЛЬНЫЙ ФАЙЛ
├── config.json.example           # 📋 Шаблон конфигурации (в Git)
├── .env                          # Секреты (SECRET_KEY) - НЕ В GIT
├── .env.example                  # 📋 Шаблон env (в Git)
├── .gitignore
├── requirements.txt
├── setup.py                      # Автоматически читает версию из config.json
├── build_macos.py                # Сборка с версией из config.json
├── Makefile                      # Команды разработки
├── babel.cfg                     # Babel конфигурация
│
├── app/                          # Основное приложение
│   ├── __init__.py              # Application Factory + load_app_info
│   ├── config.py                # Конфигурация (APP_DATA_DIR, APP_VERSION)
│   ├── exceptions.py            # Кастомные исключения
│   ├── models/                  # Модели данных
│   │   ├── __init__.py
│   │   └── server.py           # Модель VPN сервера
│   ├── services/                # Бизнес-логика (Service Layer)
│   │   ├── __init__.py         # ServiceRegistry (Dependency Injection)
│   │   ├── ssh_service.py      # SSH/SFTP операции
│   │   ├── crypto_service.py   # Шифрование/дешифрование
│   │   ├── api_service.py      # HTTP API запросы
│   │   └── data_manager_service.py  # 🆕 Управление данными (v4.0.1+)
│   ├── routes/                  # Маршруты (Blueprint Architecture)
│   │   ├── __init__.py
│   │   ├── main.py             # Основные роуты + /shutdown (v4.0.2)
│   │   └── api.py              # API endpoints + PIN auth
│   └── utils/                   # Утилиты
│       ├── __init__.py
│       ├── validators.py
│       └── decorators.py       # @require_auth, @require_pin
│
├── desktop/                     # Desktop GUI слой
│   ├── __init__.py
│   └── window.py               # 🆕 WSGI + динамические порты (v4.0.2)
│
├── templates/                   # Jinja2 шаблоны (вне app/)
│   ├── layout.html
│   ├── index.html
│   ├── index_locked.html       # PIN вход
│   ├── settings.html
│   └── ...
│
├── static/                      # Статические файлы (вне app/)
│   ├── css/
│   ├── js/
│   ├── images/
│   └── fonts/
│
├── translations/                # Flask-Babel переводы (вне app/)
│   ├── en/LC_MESSAGES/
│   ├── ru/LC_MESSAGES/
│   └── zh/LC_MESSAGES/
│
├── data/                        # Данные приложения
│   ├── servers.json.enc        # Зашифрованные серверы
│   └── merged_*.enc            # Импортированные данные
│
├── uploads/                     # Загруженные иконки серверов
├── logs/                        # Логи приложения
│   └── app.log
│
├── tests/                       # Тесты
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_services/
│   └── test_routes/
│
├── docs/                        # Документация
│   ├── project_info/
│   │   ├── PROJECT_DOCUMENTATION.md
│   │   ├── BUILD.md
│   │   ├── BACKUP_TOOLS.md
│   │   └── SECRET_KEY.md
│   ├── release_guide.md
│   └── github_push_guide.md
│
└── backup_tools/                # Инструменты резервного копирования
    └── ...
```
## 1. Application Factory Pattern

**ОБЯЗАТЕЛЬНО**: Используйте паттерн Application Factory для создания Flask-приложения.

**v4.0.3**: Application Factory автоматически загружает версию из `config.json`.

```python
# app/__init__.py
from flask import Flask
from flask_babel import Babel
from .config import config_by_name

def load_app_info(app):
    """Загрузка информации о приложении из config.json"""
    try:
        import json
        app_data_dir = app.config.get('APP_DATA_DIR')
        config_path = os.path.join(app_data_dir, 'config.json') if app_data_dir \
                      else os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                app.config['app_info'] = config.get('app_info', {})
                # Загружаем active_data_file если он есть
                if 'active_data_file' in config:
                    app.config['active_data_file'] = config['active_data_file']
    except Exception as e:
        app.logger.warning(f"Could not load app_info: {e}")
        # Fallback версия
        app.config['app_info'] = {
            "version": "4.0.3",
            "last_updated": "2025-10-12",
            "developer": "Куреин М.Н."
        }

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    
    # Инициализация расширений
    babel = Babel(app, locale_selector=get_locale)
    
    # Регистрация сервисов
    register_services(app)
    
    # Регистрация blueprints
    from .routes import main_bp, api_bp, pin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(pin_bp, url_prefix='/pin')
    
    # Обработчики ошибок
    register_error_handlers(app)
    
    # Настройка сессий (v4.0.2: уникальные cookie)
    app.config['SESSION_COOKIE_NAME'] = 'vpn_manager_session_clean'
    
    # Загрузка app_info из config.json
    load_app_info(app)
    
    # Контекстный процессор для app_info
    @app.context_processor
    def inject_app_info():
        return {'app_info': app.config.get('app_info', {})}
    
    return app
```
## 2. Конфигурация через переменные окружения + config.json

**ПРАВИЛО**: Чувствительные данные в `.env`, настройки приложения в `config.json`.

**v4.0.3**: Версия хранится **ТОЛЬКО** в `config.json` и загружается автоматически!

```python
# app/config.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_app_data_dir():
    """
    Возвращает директорию для хранения данных приложения.
    Production: ~/Library/Application Support/VPNServerManager-Clean/ (macOS)
    Development: текущая директория проекта
    """
    is_frozen = getattr(sys, 'frozen', False)
    app_name = "VPNServerManager-Clean"
    
    if is_frozen:  # Упакованное приложение
        if sys.platform == 'darwin':  # macOS
            app_data_dir = os.path.join(
                os.path.expanduser("~"), 
                "Library", "Application Support", 
                app_name
            )
        elif sys.platform == 'win32':  # Windows
            app_data_dir = os.path.join(
                os.getenv('APPDATA', os.path.expanduser("~")),
                app_name
            )
        else:  # Linux
            app_data_dir = os.path.join(
                os.path.expanduser("~"),
                ".local", "share",
                app_name
            )
    else:  # Режим разработки
        app_data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    os.makedirs(app_data_dir, exist_ok=True)
    return app_data_dir

class Config:
    """Базовая конфигурация"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    BABEL_DEFAULT_LOCALE = os.getenv('BABEL_DEFAULT_LOCALE', 'ru')
    BABEL_TRANSLATION_DIRECTORIES = 'translations'
    BABEL_SUPPORTED_LOCALES = ['ru', 'en', 'zh']
    
    # v4.0.7: Версия из config.json (fallback)
    APP_VERSION = os.getenv('APP_VERSION', '4.0.7')
    APP_NAME = 'VPNServerManager-Clean'
    APP_DATA_DIR = get_app_data_dir()
    
    # Настройки данных
    DATA_DIR = os.getenv('DATA_DIR', 'data')
    SERVERS_FILE = os.getenv('SERVERS_FILE', 'servers.json.enc')
    
    # API URLs
    IP_CHECK_API = os.getenv('IP_CHECK_API', 'https://ipinfo.io/{ip}/json')
    GENERAL_IP_TEST = os.getenv('GENERAL_IP_TEST', 'https://browserleaks.com/ip')
    
    # Настройки загрузки файлов
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '16777216'))
    ALLOWED_EXTENSIONS = {'enc', 'env', 'txt', 'zip', 'json'}
    
    # Настройки логирования
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    
class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = 'WARNING'

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    DATA_DIR = 'test_data'
    
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}
```

**config.json** (источник истины для версии):
```json
{
  "SECRET_KEY_FILE": ".env",
  "app_info": {
    "version": "4.0.7",
    "release_date": "13.10.2025",
    "developer": "Куреин М.Н.",
    "last_updated": "2025-10-13",
    "release_notes": "Security fixes: removed sensitive files from repository"
  },
  "service_urls": { ... },
  "active_data_file": "...",
  "secret_pin": { ... }
}
```
## 3. Слой сервисов (Service Layer)

**ПРИНЦИП**: Вся бизнес-логика изолирована в отдельном слое сервисов.

**v4.0.3**: Добавлен `DataManagerService` для управления данными, экспорта/импорта.

```python
# app/services/__init__.py
class ServiceRegistry:
    """Реестр сервисов (Dependency Injection)"""
    _services = {}
    
    @classmethod
    def register(cls, name: str, service):
        cls._services[name] = service
    
    @classmethod
    def get(cls, name: str):
        return cls._services.get(name)

registry = ServiceRegistry()

# app/__init__.py (регистрация сервисов)
def register_services(app):
    """Регистрация сервисов в реестре"""
    from .services.ssh_service import SSHService
    from .services.crypto_service import CryptoService
    from .services.api_service import APIService
    from .services.data_manager_service import DataManagerService
    
    registry.register('ssh', SSHService())
    registry.register('crypto', CryptoService())
    registry.register('api', APIService())
    
    # DataManagerService требует secret_key и app_data_dir
    secret_key = app.config.get('SECRET_KEY')
    app_data_dir = app.config.get('APP_DATA_DIR')
    if secret_key and app_data_dir:
        data_manager = DataManagerService(secret_key, app_data_dir)
        registry.register('data_manager', data_manager)
```

### SSHService
```python
# app/services/ssh_service.py
import paramiko
from typing import Optional
from ..exceptions import SSHConnectionError

class SSHService:
    """Сервис для работы с SSH/SFTP"""
    
    def __init__(self):
        self.client: Optional[paramiko.SSHClient] = None
    
    def connect(self, hostname: str, username: str, 
                password: Optional[str] = None,
                key_filename: Optional[str] = None) -> None:
        """Установка SSH соединения"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                hostname=hostname,
                username=username,
                password=password,
                key_filename=key_filename
            )
        except Exception as e:
            raise SSHConnectionError(f"Failed to connect: {str(e)}")
    
    def execute_command(self, command: str) -> tuple:
        """Выполнение команды на сервере"""
        if not self.client:
            raise SSHConnectionError("Not connected")
        stdin, stdout, stderr = self.client.exec_command(command)
        return stdout.read().decode(), stderr.read().decode()
    
    def disconnect(self) -> None:
        """Закрытие соединения"""
        if self.client:
            self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
```

### CryptoService
```python
# app/services/crypto_service.py
from cryptography.fernet import Fernet
import base64

class CryptoService:
    """Сервис для криптографических операций"""
    
    @staticmethod
    def generate_key() -> bytes:
        """Генерация ключа шифрования"""
        return Fernet.generate_key()
    
    @staticmethod
    def encrypt(data: str, key: bytes) -> str:
        """Шифрование данных"""
        f = Fernet(key)
        encrypted = f.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    
    @staticmethod
    def decrypt(encrypted_data: str, key: bytes) -> str:
        """Дешифрование данных"""
        f = Fernet(key)
        decrypted = f.decrypt(base64.b64decode(encrypted_data))
        return decrypted.decode()
```

### DataManagerService (v4.0.1+)
```python
# app/services/data_manager_service.py
from cryptography.fernet import Fernet
import json
import os

class DataManagerService:
    """Сервис для управления данными (экспорт/импорт/бэкап)"""
    
    def __init__(self, secret_key: str, app_data_dir: str):
        self.secret_key = secret_key
        self.app_data_dir = app_data_dir
        self.fernet = Fernet(secret_key.encode() if isinstance(secret_key, str) else secret_key)
    
    def load_servers(self, config):
        """Загрузка серверов из активного файла"""
        active_file = config.get('active_data_file')
        if not active_file or not os.path.exists(active_file):
            return []
        
        try:
            with open(active_file, 'rb') as f:
                encrypted_data = f.read()
            decrypted = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted.decode('utf-8'))
        except Exception as e:
            logger.error(f"Error loading servers: {e}")
            return []
    
    def save_servers(self, servers, filepath):
        """Сохранение серверов в зашифрованный файл"""
        try:
            json_data = json.dumps(servers, ensure_ascii=False, indent=2)
            encrypted = self.fernet.encrypt(json_data.encode('utf-8'))
            with open(filepath, 'wb') as f:
                f.write(encrypted)
            return True
        except Exception as e:
            logger.error(f"Error saving servers: {e}")
            return False
    
    def export_data(self, export_dir):
        """Экспорт данных"""
        # ... реализация экспорта
    
    def import_data(self, file_path):
        """Импорт данных"""
        # ... реализация импорта
```
4. Blueprints для модульности
ПРАВИЛО: Разделяйте функциональность на blueprints.

python
# app/routes/main.py
from flask import Blueprint, render_template
from flask_babel import _

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html', title=_('Home'))
5. Обработка исключений
ПРИНЦИП: Создавайте кастомные исключения и централизованные обработчики.

python
# app/exceptions.py
class AppException(Exception):
    """Базовое исключение приложения"""
    status_code = 500
    
class SSHConnectionError(AppException):
    status_code = 503
    
class CryptoError(AppException):
    status_code = 500

# app/__init__.py (продолжение)
def register_error_handlers(app):
    @app.errorhandler(AppException)
    def handle_app_exception(error):
        response = {
            'error': error.__class__.__name__,
            'message': str(error)
        }
        return response, error.status_code
6. Интернационализация (i18n)
ПРАВИЛО: Используйте Flask-Babel для всех пользовательских текстов.

python
# app/__init__.py
from flask_babel import Babel

def get_locale():
    """Определение локали пользователя"""
    return request.accept_languages.best_match(['en', 'ru'])

babel = Babel(app, locale_selector=get_locale)

# В шаблонах и коде
from flask_babel import gettext as _
message = _('Welcome to application')
## 7. Desktop GUI с pywebview (v4.0.2 - Multi-App Support)

**АРХИТЕКТУРА**: Разделяйте web и desktop слои.

**v4.0.2+**: WSGI сервер с динамическим портом (порт 0) для параллельного запуска.

```python
# desktop/window.py
import webview
import threading
import time
import signal
from wsgiref.simple_server import make_server
from app import create_app

# Глобальные переменные для управления сервером
SERVER_PORT = None
_WSGI_SERVER = None

class DesktopApp:
    def __init__(self, config_name='production'):
        self.config_name = config_name
        self.app = None
        self.window = None
        self.server_thread = None
    
    def create_flask_app(self):
        """Создание Flask приложения"""
        self.app = create_app(self.config_name)
        return self.app
    
    def start_flask_server(self):
        """Запуск Flask сервера с динамическим портом"""
        global SERVER_PORT, _WSGI_SERVER
        
        if self.app:
            # Порт 0 = ОС автоматически выбирает свободный порт
            _WSGI_SERVER = make_server('127.0.0.1', 0, self.app)
            SERVER_PORT = _WSGI_SERVER.server_port
            
            logger.info(f"🚀 Flask сервер запущен на http://127.0.0.1:{SERVER_PORT}")
            _WSGI_SERVER.serve_forever()
    
    def start(self):
        """Запуск desktop приложения"""
        global SERVER_PORT
        
        # Создаем Flask приложение
        self.create_flask_app()
        
        # Запускаем Flask сервер в отдельном потоке
        self.server_thread = threading.Thread(target=self.start_flask_server, daemon=True)
        self.server_thread.start()
        
        # Ожидание инициализации сервера
        for _ in range(100):
            if SERVER_PORT:
                break
            time.sleep(0.05)
        
        # Создаем окно pywebview с динамическим URL
        self.window = webview.create_window(
            'VPN Server Manager - Clean',
            f'http://127.0.0.1:{SERVER_PORT}',  # Динамический порт!
            width=1200,
            height=800,
            resizable=True
        )
        
        # Обработчик закрытия
        self.window.events.closing += self.on_closing
        
        webview.start()
    
    def on_closing(self):
        """Graceful shutdown"""
        global SERVER_PORT, _WSGI_SERVER
        if SERVER_PORT and _WSGI_SERVER:
            _WSGI_SERVER.shutdown()

# run.py (v4.0.3 с версией из config.json)
import sys
import os
import socket
import logging

def find_free_port(start_port=5000, max_attempts=100):
    """Находит свободный порт для web режима"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find free port")

def main():
    if '--desktop' in sys.argv:
        # Desktop режим (порт автоматический)
        from desktop.window import DesktopApp
        config_name = 'development' if '--debug' in sys.argv else 'production'
        app = DesktopApp(config_name)
        app.start()
    else:
        # Web режим (динамический порт)
        from app import create_app
        config_name = 'development' if '--debug' in sys.argv else 'production'
        app = create_app(config_name)
        
        port = find_free_port(5000)
        
        # Загружаем версию из config.json
        import json
        version = "4.0.3"
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                version = config['app_info']['version']
        except:
            pass
        
        print(f"\n🌐 VPN Server Manager v{version}")
        print(f"📡 Web server: http://127.0.0.1:{port}\n")
        
        app.run(host='127.0.0.1', port=port, debug=(config_name == 'development'))

if __name__ == '__main__':
    main()
```
8. Работа с внешними API (requests)
ПРИНЦИП: Изолируйте HTTP-запросы в отдельный сервис с retry-логикой.

python
# app/services/api_service.py
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Optional

class APIService:
    """Сервис для работы с внешними API"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Создание сессии с retry-логикой"""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """GET запрос"""
        url = f"{self.base_url}/{endpoint}"
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
9. Безопасность
ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА:

Никогда не храните секреты в коде - используйте .env
Валидируйте все входные данные
Используйте HTTPS в production
Применяйте CSP headers
Шифруйте чувствительные данные с помощью cryptography
python
# app/utils/validators.py
from werkzeug.security import check_password_hash, generate_password_hash

def validate_password(password: str) -> bool:
    """Валидация пароля"""
    return (
        len(password) >= 8 and
        any(c.isupper() for c in password) and
        any(c.isdigit() for c in password)
    )

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return generate_password_hash(password, method='pbkdf2:sha256')
10. Логирование
ПРИНЦИП: Структурированное логирование на всех уровнях.

python
# app/__init__.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(app):
    if not app.debug:
        file_handler = RotatingFileHandler(
            'logs/app.log',
            maxBytes=10240000,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application startup')
11. Тестирование
ОБЯЗАТЕЛЬНО: Покрывайте тестами критичную функциональность.

python
# tests/conftest.py
import pytest
from app import create_app

@pytest.fixture
def app():
    app = create_app('testing')
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

# tests/test_services/test_crypto_service.py
from app.services.crypto_service import CryptoService

def test_encryption_decryption():
    service = CryptoService()
    key = service.generate_key()
    
    original = "secret data"
    encrypted = service.encrypt(original, key)
    decrypted = service.decrypt(encrypted, key)
    
    assert decrypted == original
    assert encrypted != original
## 12. Dependency Injection (Service Registry)

**ПРИНЦИП**: Используйте DI для управления зависимостями сервисов.

**v4.0.3**: Все сервисы регистрируются в `ServiceRegistry` при инициализации приложения.

```python
# app/services/__init__.py
class ServiceRegistry:
    """Реестр сервисов для Dependency Injection"""
    _services = {}
    
    @classmethod
    def register(cls, name: str, service):
        """Регистрация сервиса"""
        cls._services[name] = service
    
    @classmethod
    def get(cls, name: str):
        """Получение сервиса"""
        return cls._services.get(name)
    
    @classmethod
    def clear(cls):
        """Очистка реестра (для тестов)"""
        cls._services = {}

registry = ServiceRegistry()

# app/__init__.py (регистрация при создании приложения)
def register_services(app):
    """Регистрация всех сервисов"""
    from .services.ssh_service import SSHService
    from .services.crypto_service import CryptoService
    from .services.api_service import APIService
    from .services.data_manager_service import DataManagerService
    
    # Базовые сервисы
    registry.register('ssh', SSHService())
    registry.register('crypto', CryptoService())
    registry.register('api', APIService())
    
    # DataManagerService с зависимостями
    secret_key = app.config.get('SECRET_KEY')
    app_data_dir = app.config.get('APP_DATA_DIR')
    if secret_key and app_data_dir:
        registry.register('data_manager', DataManagerService(secret_key, app_data_dir))

# Использование в routes
from app.services import registry

@main_bp.route('/servers')
def list_servers():
    data_manager = registry.get('data_manager')
    servers = data_manager.load_servers(current_app.config)
    return render_template('index.html', servers=servers)
```
Контрольный список (Checklist)
 Application Factory реализован
 Все секреты в .env
 Blueprints для модульности
 Service Layer для бизнес-логики
 Кастомные исключения и обработчики
 Flask-Babel настроен
 Валидация входных данных
 Логирование настроено
 Тесты написаны
 Документация актуальна
 .gitignore содержит .env, __pycache__, etc.
 Requirements.txt актуален
Команды для работы
bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt

# Инициализация переводов
pybabel extract -F babel.cfg -o messages.pot .
pybabel init -i messages.pot -d app/translations -l ru
pybabel compile -d app/translations

# Запуск тестов
pytest

# Запуск приложения
python run.py              # Web режим
python run.py --desktop    # Desktop режим
Примечания
Всегда следуйте PEP 8
Используйте type hints (Python 3.10+)
Документируйте публичные методы docstrings
Версионируйте API endpoints
Регулярно обновляйте зависимости (pip-audit)
