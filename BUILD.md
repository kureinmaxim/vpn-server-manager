# Руководство по сборке VPN Server Manager

## Требования

- Python 3.13+
- pip
- Git (опционально)
- Inno Setup для Windows-инсталлятора

## Быстрый старт

### Windows PowerShell

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

copy env.example .env
python generate_key.py
copy config\config.json.template config.json
```

Если `venv` ещё не создан, некоторые команды можно запускать напрямую через системный `python`, но для разработки и сборки рекомендуется полноценное окружение.

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt

cp env.example .env
python3 generate_key.py
cp config/config.json.template config.json
```

## Конфигурация

Обязательные локальные файлы:

| Файл | Назначение | Статус |
|------|------------|--------|
| `.env` | `SECRET_KEY`, runtime-параметры | Не в Git |
| `config.json` | локальные runtime-настройки, PIN, пути к данным | Не в Git |
| `config/config.json.template` | источник правды для версии релиза | В Git |

Важно:

- `config.json` не является источником версии репозитория;
- версия релиза управляется через `tools/update_version.py`;
- перед релизом сверяйтесь с `VERSION_MANAGEMENT.md`.

## Запуск приложения

### Web

```text
python run.py
```

### Desktop

```text
python run_desktop.py
```

### Debug

```text
python run.py --debug
```

## Сборка инсталляторов

### Windows

PowerShell:

```powershell
.\build_windows.ps1
```

CMD:

```cmd
build_windows.bat
```

Результат:

```text
installer_output/VPN-Server-Manager-Setup-vX.Y.Z.exe
```

Если установка зависимостей в Windows падает с `ProxyError` или `No matching distribution found`, см. `docs/WINDOWS_PROXY_TROUBLESHOOTING.md`.

### macOS

Сборка выполняется через `build_macos.py`, который использует PyInstaller.

```bash
python3 build_macos.py
```

Ожидаемые артефакты:

```text
dist/VPNServerManager-Clean.app
dist/VPNServerManager-Clean_Installer.dmg
```

## Переводы

После изменения `.po` файлов обязательно компилируйте `.mo`:

### Windows PowerShell

```powershell
python -m babel.messages.frontend compile -d translations
```

### macOS / Linux

```bash
pybabel compile -d translations
```

## Тестирование

```text
pytest
pytest --cov=app tests/
```

Если зависимости тестов ещё не установлены:

```text
python -m pip install pytest pytest-cov
```

## Частые проблемы

### PowerShell не запускает `venv\Scripts\python.exe`

Используйте префикс `.\`:

```powershell
.\venv\Scripts\python.exe tools\update_version.py status
```

Если `venv` отсутствует:

```powershell
python tools\update_version.py status
```

### Версия в UI и сборке не совпадает

Проверьте:

- `config/config.json.template`
- `VERSION_MANAGEMENT.md`
- `docs/release_guide.md`

И затем запустите:

```text
python tools/update_version.py status
```

## Связанные документы

- `README.md`
- `VERSION_MANAGEMENT.md`
- `docs/release_guide.md`
- `docs/WINDOWS_PROXY_TROUBLESHOOTING.md`
