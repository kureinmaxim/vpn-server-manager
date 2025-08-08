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
├── PROJECT_STRUCTURE.md         # Структура проекта (этот файл)
├── SECRET_KEY.md                # Система шифрования
├── BUILD.md                     # Инструкции по сборке
├── CHANGELOG.md                 # История изменений
├── CONTRIBUTING.md              # Руководство по участию
├── LICENSE                      # Лицензия MIT
├── .gitignore                   # Исключения для Git
├── generate_key.py              # Утилита генерации SECRET_KEY
├── decrypt_tool.py              # Инструмент для расшифровки данных
├── pin_auth.py                  # Система PIN-аутентификации
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
│   └── i18n/                    # Документация по локализации
│       ├── README.md
│       ├── flask-babel.md
│       ├── babel-cli-workflow.md
│       ├── auto-translate.md
│       ├── add-language.md
│       ├── troubleshooting.md
│       └── pyinstaller.md
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
- Для упаковки в `.app` добавляйте `translations` в сборку (см. docs/i18n/pyinstaller.md)
- Данные пользователя сохраняются в `~/Library/Application Support/VPNServerManager-Clean` (см. README)