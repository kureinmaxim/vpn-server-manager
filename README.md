# VPN Server Manager v4.2.2

Приложение для управления VPN-серверами с гибридной архитектурой `Flask + PyWebView`, шифрованием данных и поддержкой desktop/web режима.

![VPN Server Manager](static/VPSc.png)

## Возможности

- Шифрование данных через Fernet
- Desktop и Web режимы
- PIN-защита
- Импорт и экспорт данных
- SSH-мониторинг серверов
- Многоязычный интерфейс
- Офлайн-режим

## Требования

- Python 3.13+
- pip

## Установка

### Windows

Автоматический вариант:

```cmd
setup_windows.bat
start_windows.bat
```

Ручной вариант в PowerShell:

```powershell
git clone https://github.com/kureinmaxim/vpn-server-manager.git
cd vpn-server-manager

python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

copy env.example .env
python generate_key.py
copy config\config.json.template config.json

python -m babel.messages.frontend compile -d translations
python run.py
```

Если виртуальное окружение ещё не создано, служебные скрипты вроде `tools/update_version.py` можно запускать напрямую через системный `python`.

### macOS / Linux

```bash
git clone https://github.com/kureinmaxim/vpn-server-manager.git
cd vpn-server-manager

python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt

cp env.example .env
python3 generate_key.py
cp config/config.json.template config.json

python -m babel.messages.frontend compile -d translations
python3 run.py
```

## Запуск

```text
Web:     python run.py
Desktop: python run_desktop.py
Debug:   python run.py --debug
```

## Версии и конфигурация

- Источник правды для версии релиза: `config/config.json.template`
- Локальный `config.json` нужен для runtime-настроек и не является источником версии репозитория
- Для синхронизации версий используйте `tools/update_version.py`

## Документация

- [Индекс документации](docs/INDEX.md)
- [Руководство по сборке](BUILD.md)
- [Управление версиями](VERSION_MANAGEMENT.md)
- [Релизный процесс](docs/release_guide.md)
- [Windows proxy troubleshooting](docs/WINDOWS_PROXY_TROUBLESHOOTING.md)
- [Мониторинг](docs/README_MONITORING.md)
- [Docker Guide](docs/DOCKER_GUIDE.md)

## Changelog

См. `CHANGELOG.md`.

## Лицензия

MIT License. См. `LICENSE`.
