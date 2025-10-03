# Структура Проекта VPN Server Manager

Этот документ описывает организацию файлов и папок в проекте, а также основной алгоритм работы приложения.

## Дерево Проекта

```
VPNserverManage-Clean/
│
├── app.py                       # Основной файл (Flask + PyWebView)
├── build_macos.py               # Сборка .app и .dmg для macOS
├── requirements.txt             # Зависимости Python
├── config.json                  # Конфигурация приложения (версия, URL-ы)
├── VPNServerManager-Clean.spec  # Конфиг PyInstaller
├── README.md                    # Главная страница проекта
├── CHANGELOG.md                 # История изменений
├── LICENSE                      # Лицензия MIT
├── .gitignore                   # Исключения для Git
├── generate_key.py              # Утилита генерации SECRET_KEY
├── decrypt_tool.py              # Инструмент для расшифровки данных
├── pin_auth.py                  # Система PIN-аутентификации
├── pin_block_state.json         # Состояние блокировки PIN-кода
│
├── data/                        # Данные проекта (зашифрованные и служебные)
│   ├── servers.json.enc
│   ├── hints.json
│   └── merged_*.enc
│
├── static/
│   ├── css/
│   ├── images/
│   ├── fonts/
│   └── js/
│
├── templates/                   # HTML-шаблоны интерфейса
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
├── translations/                # Переводы (.po/.mo)
│   ├── en/LC_MESSAGES/messages.{po,mo}
│   ├── zh/LC_MESSAGES/messages.{po,mo}
│   └── ru/LC_MESSAGES/          # (опционально)
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
└── venv/                        # Виртуальное окружение Python
```

## Примечания
- Переводы компилируются в `.mo` через `pybabel compile -d translations`
- Для упаковки в `.app` добавляйте `translations` в сборку (см. docs/lessons/i18n/pyinstaller.md)
- Данные пользователя сохраняются в `~/Library/Application Support/VPNServerManager-Clean` (см. README)