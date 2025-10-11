# Структура Проекта VPN Server Manager v4.0.0

Этот документ описывает новую модульную архитектуру проекта, созданную в соответствии с современными принципами разработки Flask-приложений.

## 🏗️ Новая архитектура v4.0.0

### Дерево Проекта

```
VPNserverManage-Clean/
│
├── run.py                       # Новая точка входа (web/desktop режимы)
├── app/                         # Основное приложение (модульная архитектура)
│   ├── __init__.py             # Application Factory
│   ├── config.py               # Конфигурация через переменные окружения
│   ├── exceptions.py           # Кастомные исключения
│   ├── models/                 # Модели данных
│   │   ├── __init__.py
│   │   └── server.py
│   ├── services/               # Бизнес-логика (Service Layer)
│   │   ├── __init__.py
│   │   ├── ssh_service.py      # SSH/SFTP сервисы
│   │   ├── crypto_service.py   # Криптографические операции
│   │   └── api_service.py      # HTTP API сервисы
│   ├── routes/                 # Маршруты (Blueprint Architecture)
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── api.py
│   └── utils/                  # Утилиты
│       ├── __init__.py
│       ├── validators.py
│       └── decorators.py
│
├── desktop/                    # Desktop GUI слой
│   ├── __init__.py
│   └── window.py
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
├── RESTRUCTURING_REPORT.md     # Отчет о реструктуризации
├── MIGRATION_GUIDE.md          # Руководство по миграции
├── CHANGELOG.md                # История изменений
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

### Service Layer
- **SSH Service**: `app/services/ssh_service.py` - SSH/SFTP операции
- **Crypto Service**: `app/services/crypto_service.py` - Шифрование/дешифрование
- **API Service**: `app/services/api_service.py` - HTTP запросы
- **Registry**: `app/services/__init__.py` - Dependency Injection

### Blueprint Architecture
- **Main Blueprint**: `app/routes/main.py` - Основные маршруты
- **API Blueprint**: `app/routes/api.py` - REST API endpoints

### Models
- **Server Model**: `app/models/server.py` - Модель сервера с валидацией

### Utils
- **Validators**: `app/utils/validators.py` - Валидация данных
- **Decorators**: `app/utils/decorators.py` - Декораторы безопасности

### Desktop Layer
- **Desktop App**: `desktop/window.py` - PyWebView GUI

### Testing
- **Test Configuration**: `tests/conftest.py` - Pytest конфигурация
- **Service Tests**: `tests/test_services/` - Тесты сервисов
- **Route Tests**: `tests/test_routes/` - Тесты маршрутов

## 🚀 Запуск приложения

### Web режим
```bash
python run.py
```

### Desktop режим
```bash
python run.py --desktop
```

### Debug режим
```bash
python run.py --debug
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

## Примечания
- Переводы компилируются в `.mo` через `pybabel compile -d translations`
- Для упаковки в `.app` добавляйте `translations` в сборку (см. docs/lessons/i18n/pyinstaller.md)
- Данные пользователя сохраняются в `~/Library/Application Support/VPNServerManager-Clean` (см. README)