# Структура Проекта VPN Server Manager v4.0.5

Этот документ описывает новую модульную архитектуру проекта, созданную в соответствии с современными принципами разработки Flask-приложений.

## 🏗️ Новая архитектура v4.0.5

### ✨ Последние обновления (v4.0.5)
- 🐛 **Функция "Сохранить как PNG"**: Полностью реализована с сохранением в Downloads
- 🔐 **PIN аутентификация**: Исправлено отображение текста ошибки при неправильном PIN
- 🌐 **SSH подключение**: Добавлена поддержка нестандартных SSH портов (2222)
- 🌍 **Переводы**: Обновлены переводы для RU, EN, ZH языков

### ✨ Обновления v4.0.4
- 🪟 **Поддержка Windows**: Автоматические скрипты установки и запуска
- 🐳 **Docker документация**: Полная документация для Windows и macOS

### ✨ Обновления v4.0.3
- 🎯 **Централизованная версия**: Версия автоматически из `config.json`
- 🚪 **Система выхода**: Endpoints `/pin/exit_app`, `/pin/logout`, `/pin/check_auth`
- 🔐 **Управление сессиями**: `private_mode=True`, сессии не сохраняются между запусками
- 🎨 **UI/UX улучшения**: Окно 880px, футер, информация о сервере (URL и порт)
- 🌐 **Локализация**: Добавлены переводы, локализованные диалоги выхода/закрытия
- 🔧 **Исправления**: Страница "Управление подсказками" теперь работает
- 🚀 **Multi-App Support**: Параллельный запуск нескольких экземпляров без конфликтов
- 🎯 **Динамические порты**: WSGI сервер с автоматическим выделением портов
- 🔒 **Изолированные сессии**: Уникальные cookie для каждого экземпляра
- ⚡ **Graceful Shutdown**: Корректное завершение с освобождением ресурсов
- 🐛 **Frozen режим исправлен**: Корректные пути для macOS .app
- 🪟 **Desktop launcher**: `launch_gui.py` для запуска из Finder
- 🎨 **Иконка восстановлена**: PNG → ICNS конвертация

### Дерево Проекта

```
VPNserverManage-Clean/
│
├── run.py                       # Новая точка входа (web/desktop режимы)
├── launch_gui.py                # 🆕 Desktop launcher для Finder (v4.0.3)
├── run_desktop.py               # Обёртка для --desktop режима
├── config.json                  # 🎯 Конфигурация + версия 4.0.5
├── Info.plist.template          # 🆕 Шаблон для macOS (v4.0.3)
├── app/                         # Основное приложение (модульная архитектура)
│   ├── __init__.py             # Application Factory + уникальные cookie-сессии
│   ├── config.py               # Конфигурация через переменные окружения
│   ├── exceptions.py           # Кастомные исключения
│   ├── models/                 # Модели данных
│   │   ├── __init__.py
│   │   └── server.py
│   ├── services/               # Бизнес-логика (Service Layer)
│   │   ├── __init__.py
│   │   ├── ssh_service.py      # SSH/SFTP сервисы
│   │   ├── crypto_service.py   # Криптографические операции
│   │   ├── api_service.py      # HTTP API сервисы
│   │   └── data_manager_service.py  # Управление данными (v4.0.1+)
│   ├── routes/                 # Маршруты (Blueprint Architecture)
│   │   ├── __init__.py
│   │   ├── main.py             # + эндпоинт /shutdown (v4.0.2)
│   │   └── api.py
│   └── utils/                  # Утилиты
│       ├── __init__.py
│       ├── validators.py
│       └── decorators.py
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
├── build_macos.py              # Сборка .app и .dmg для macOS
├── requirements.txt            # Зависимости Python
├── config.json                 # Конфигурация приложения (legacy)
├── env.example                 # Пример переменных окружения
├── setup.py                    # Установка пакета
├── Makefile                    # Команды разработки
├── Dockerfile                  # Контейнеризация
├── docker-compose.yml          # Docker Compose
├── pytest.ini                 # Настройки тестов
├── VPNServerManager-Clean.spec # Конфиг PyInstaller
├── README.md                   # Главная страница проекта
├── README_NEW_STRUCTURE.md     # Документация новой архитектуры
├── MULTI_APP_IMPLEMENTATION.md # Спецификация Multi-App Support
├── ArchitecturalRules.md       # Архитектурные правила проекта
├── CHANGELOG.md                # История изменений (v4.0.2)
├── LICENSE                     # Лицензия MIT
├── .gitignore                  # Исключения для Git
├── generate_key.py             # Утилита генерации SECRET_KEY
├── decrypt_tool.py             # Инструмент для расшифровки данных
├── test_basic.py               # Базовые тесты
├── pin_auth.py                 # Система PIN-аутентификации (legacy)
├── pin_block_state.json        # Состояние блокировки PIN-кода
│
├── data/                       # Данные проекта (зашифрованные и служебные)
│   ├── servers.json.enc
│   ├── hints.json
│   └── merged_*.enc
│
├── static/                     # Статические файлы
│   ├── css/
│   ├── images/
│   ├── fonts/
│   └── js/
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
│   └── manage_hints.html
│
├── translations/               # Переводы (.po/.mo)
│   ├── en/LC_MESSAGES/messages.{po,mo}
│   ├── zh/LC_MESSAGES/messages.{po,mo}
│   └── ru/LC_MESSAGES/         # (опционально)
│
├── docs/
│   ├── project_info/            # Основная документация проекта
│   │   ├── README.md
│   │   ├── PROJECT_STRUCTURE.md # Этот файл
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

## 🔧 Ключевые компоненты новой архитектуры

### Application Factory Pattern
- **Файл**: `app/__init__.py`
- **Функция**: `create_app(config_name)`
- **Назначение**: Создание Flask-приложения с различными конфигурациями
- **v4.0.2**: Уникальные cookie-сессии (`SESSION_COOKIE_NAME = 'vpn_manager_session_clean'`)

### Service Layer
- **SSH Service**: `app/services/ssh_service.py` - SSH/SFTP операции
- **Crypto Service**: `app/services/crypto_service.py` - Шифрование/дешифрование
- **API Service**: `app/services/api_service.py` - HTTP запросы
- **Data Manager Service**: `app/services/data_manager_service.py` - Управление данными (v4.0.1+)
- **Registry**: `app/services/__init__.py` - Dependency Injection

### Blueprint Architecture
- **Main Blueprint**: `app/routes/main.py` - Основные маршруты + `/shutdown` (v4.0.2) + `/manage_hints`, `/add_hint`, `/delete_hint` (v4.0.3)
- **API Blueprint**: `app/routes/api.py` - REST API endpoints
- **PIN Blueprint**: `app/routes/api.py` - PIN аутентификация + `/logout`, `/exit_app`, `/check_auth` (v4.0.3)

### Models
- **Server Model**: `app/models/server.py` - Модель сервера с валидацией

### Utils
- **Validators**: `app/utils/validators.py` - Валидация данных
- **Decorators**: `app/utils/decorators.py` - Декораторы безопасности

### Desktop Layer (v4.0.2 - Multi-App Support, v4.0.3 - Exit System)
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

## 🚀 Запуск приложения

### Web режим (с автоматическим выбором порта)
```bash
python run.py
# 🌐 VPN Server Manager v4.0.5
# 📡 Web server: http://127.0.0.1:5000 (или следующий свободный)
```

### Desktop режим (с динамическим портом v4.0.5)
```bash
python run.py --desktop
# 🚀 Flask сервер запущен на http://127.0.0.1:XXXXX
# Порт назначается автоматически ОС!
```

### Debug режим
```bash
python run.py --debug
```

### 🎯 Параллельный запуск (v4.0.5)
```bash
# Терминал 1
python run.py --desktop  # Порт: 52341

# Терминал 2
python run.py --desktop  # Порт: 52342 (автоматически!)

# Результат: Два независимых экземпляра без конфликтов!
```

## 🛠️ Инструменты разработки

### Makefile команды
- `make install-dev` - Установка зависимостей для разработки
- `make test` - Запуск тестов
- `make lint` - Проверка качества кода
- `make format` - Форматирование кода
- `make all` - Все проверки

### Docker
- `Dockerfile` - Контейнеризация приложения
- `docker-compose.yml` - Оркестрация сервисов

### Тестирование
- `pytest.ini` - Конфигурация тестов
- Покрытие кода и интеграционные тесты
```

## 🎯 Архитектурные преимущества v4.0.5

### Multi-App Support
- ✅ **Динамические порты**: Никогда не будет конфликтов "Address already in use"
- ✅ **Изолированные сессии**: Уникальные cookie для каждого экземпляра
- ✅ **Параллельная работа**: Неограниченное количество экземпляров
- ✅ **Graceful Shutdown**: Корректное освобождение ресурсов

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

### Технические детали
- **WSGI**: `wsgiref.simple_server.make_server('127.0.0.1', 0, app)`
- **Cookie**: `SESSION_COOKIE_NAME = 'vpn_manager_session_clean'`
- **Shutdown**: Эндпоинт `/shutdown` + обработчик `on_closing`
- **Exit**: `logout()` → `session.clear()` → `window.destroy()` → `os._exit(0)`
- **Session**: `private_mode=True`, отключен `SESSION_TYPE='filesystem'`
- **Документация**: [MULTI_APP_IMPLEMENTATION.md](../../MULTI_APP_IMPLEMENTATION.md)

## 📝 Примечания

### Общие
- Переводы компилируются в `.mo` через `pybabel compile -d translations`
- Для упаковки в `.app` добавляйте `translations` в сборку (см. docs/lessons/i18n/pyinstaller.md)
- **v4.0.3**: Версия автоматически загружается из `config.json`
- **v4.0.3**: Каждый экземпляр автоматически получает свободный порт от ОС

### Пути данных (v4.0.3)

#### Production (macOS frozen .app):
- **Данные**: `~/Library/Application Support/VPNServerManager-Clean/data/`
- **Логи**: `~/Library/Logs/VPNServerManager/app.log`
- **Загрузки**: `~/Library/Application Support/VPNServerManager-Clean/uploads/`
- **Конфигурация**: Встроена в .app bundle

#### Development (исходники):
- **Данные**: `./data/`
- **Логи**: `./logs/app.log`
- **Загрузки**: `./uploads/`
- **Конфигурация**: `./config.json`

### Frozen режим (v4.0.3)
- **Launcher**: `launch_gui.py` - автоматическое логирование и инициализация
- **Detection**: `sys.frozen` для определения режима
- **Info.plist**: `NSPrincipalClass=NSApplication` для GUI
- **Иконка**: `icon_clean.icns` (16x16 → 1024x1024)