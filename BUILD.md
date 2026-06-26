# Руководство по сборке VPN Server Manager

Документ описывает, как правильно собрать дистрибутивы: **инсталлятор для Windows**
и **приложение для macOS**.

## Две модели сборки (важно понимать различие)

| Платформа | Что получается | Нужен ли Python у пользователя |
|-----------|----------------|-------------------------------|
| **Windows** | **Source-инсталлятор** (Inno Setup): `VPN-Server-Manager-Setup-vX.Y.Z.exe`. Внутри — исходники приложения; при установке создаётся `venv` и ставятся зависимости. | **Да.** Python 3.13+ должен быть установлен на машине пользователя. |
| **macOS** | **Автономное `.app`** (PyInstaller) + `.dmg`. Python и зависимости упакованы внутрь. | Нет. |

> На Windows **нет** отдельного PyInstaller-`.exe` самого приложения. «Exe» — это
> сам **инсталлятор**, который разворачивает исходники и поднимает `venv` через
> `setup_windows.bat`, а запускает приложение `start_windows.bat`.

## Требования

- Python 3.13+ и `pip`
- **Inno Setup 6** (для Windows-инсталлятора) — https://jrsoftware.org/isdl.php
  - скрипты ждут компилятор по пути `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`
    (поправьте `$IsccPath` / `ISCC_PATH` в `build_windows.ps1` / `.bat`, если иной)
- macOS + Xcode CLT (`sips`, `iconutil`) — для сборки `.app`
- виртуальное окружение `venv` с зависимостями из `requirements.txt` — для сборки
  на macOS и для шагов ниже (системный `python3` их не содержит)

## Подготовка окружения (macOS / Linux)

Перед сборкой и шагами 1–2 поднимите `venv` и установите зависимости:

```bash
python3 -m venv venv          # один раз, если venv ещё нет
source venv/bin/activate
pip install -r requirements.txt
```

Дальше в этом документе `python` / `python3` подразумевают **активированный venv**.
Без активации на macOS/Linux можно вызывать явно: `venv/bin/python3 …`.

Windows (PowerShell): `.\venv\Scripts\Activate.ps1`

---

## Шаг 1. Поднять версию (ОБЯЗАТЕЛЬНО через инструмент)

Версия хранится в нескольких файлах и **должна быть синхронизирована**. Никогда
не правьте версию вручную — используйте `tools/update_version.py`, он обновляет
сразу всё: `config/config.json.template`, **`vpn-manager-installer.iss`**
(`MyAppVersion`), `README.md`, `env.example`, `app/config.py`, `app/__init__.py`,
`setup.py` и `CHANGELOG.md`.

```bash
python tools/update_version.py status            # показать текущую версию во всех файлах
python tools/update_version.py bump patch        # patch / minor / major
python tools/update_version.py set 4.3.1         # или задать явно
```

> ⚠️ Если версия в `config/config.json.template` и `vpn-manager-installer.iss`
> разойдётся, Inno соберёт файл с одним именем, а `build_windows.ps1` будет искать
> другое → ошибка «Installer not found». Поэтому — только через `update_version.py`.

## Шаг 2. Скомпилировать переводы (`.po → .mo`)

Файлы `.mo` лежат в `.gitignore` (это артефакты) и **не хранятся в репозитории**.
Без них переключение языков не работает, а инсталлятор увезёт интерфейс без
переводов. Поэтому **перед сборкой** скомпилируйте каталоги:

```bash
# из корня проекта
python -m babel.messages.frontend compile -d translations
# (или, если установлен pybabel:)  pybabel compile -d translations
```

Появятся `translations/<lang>/LC_MESSAGES/messages.mo`, которые попадут в
инсталлятор. (В рантайме приложение дополнительно компилирует `.mo`
самостоятельно при старте, но при сборке их лучше включить явно.)

`build_windows.ps1` выполняет этот шаг автоматически; при ручной сборке/отладке
делайте его сами.

---

## Шаг 3. Сборка

### Windows (инсталлятор)

Из корня проекта:

```powershell
.\build_windows.ps1
```

или в CMD:

```cmd
build_windows.bat
```

Что делает скрипт: читает версию из `config/config.json.template`, проверяет
наличие Inno Setup и нужных файлов, компилирует переводы, чистит `venv`/кеши,
запускает `ISCC.exe vpn-manager-installer.iss` и считает SHA-256.

Результат:

```text
installer_output/VPN-Server-Manager-Setup-vX.Y.Z.exe
installer_output/checksum.txt
```

Что произойдёт у пользователя при запуске инсталлятора:
1. проверка наличия Python (если нет — подсказка скачать с python.org с «Add to PATH»);
2. установка файлов в `%LOCALAPPDATA%\Programs\VPN Server Manager` (права `lowest`);
3. запуск `setup_windows.bat` — создание `venv` и установка `requirements.txt` (3–5 мин);
4. ярлыки в меню Пуск / на рабочем столе на `start_windows.bat`.

> Пользовательские данные (`.env`, `config.json`, `data\`) **не** входят в
> инсталлятор и **не** удаляются при апдейте/деинсталляции (по выбору пользователя).

### macOS (приложение `.app` + `.dmg`)

Из корня проекта, с активированным `venv` (см. «Подготовка окружения»):

```bash
source venv/bin/activate
python3 build_macos.py
```

Без активации:

```bash
venv/bin/python3 build_macos.py
```

Использует PyInstaller; иконки `.icns` генерируются из `static/images/icon.png`.
Артефакты:

```text
dist/VPNServerManager-Clean.app
dist/VPNServerManager-Clean_Installer.dmg
```

---

## Локальная разработка (без сборки)

```bash
python -m venv venv
# Windows:  .\venv\Scripts\Activate.ps1     |  macOS/Linux:  source venv/bin/activate
python -m pip install -r requirements.txt

cp env.example .env            # Windows: copy env.example .env
python generate_key.py         # сгенерирует SECRET_KEY в .env
cp config/config.json.template config.json
python -m babel.messages.frontend compile -d translations   # .mo для переключения языков

python run.py                  # Web-режим
python run_desktop.py          # Desktop (PyWebView)
python run.py --debug          # отладка
```

Обязательные локальные файлы (не в Git):

| Файл | Назначение |
|------|------------|
| `.env` | `SECRET_KEY` и runtime-параметры |
| `config.json` | локальные настройки, PIN, пути к данным |
| `translations/**/*.mo` | скомпилированные переводы (генерируются, см. Шаг 2) |

`config/config.json.template` — источник правды для версии релиза (в Git).

---

## Тестирование

```bash
pytest
pytest --cov=app tests/
python -m pip install pytest pytest-cov   # если зависимостей тестов ещё нет
```

## Частые проблемы

### `ModuleNotFoundError: No module named 'dotenv'` (macOS)
Скрипт `build_macos.py` запущен системным `python3`, а не из `venv`. Активируйте
окружение (`source venv/bin/activate`) или используйте `venv/bin/python3 build_macos.py`.
При первой настройке: `pip install -r requirements.txt`.

### `Installer not found` после Inno Setup
Версии в `config/config.json.template` и `vpn-manager-installer.iss` разошлись.
Прогоните `python tools/update_version.py status`, при расхождении —
`python tools/update_version.py set X.Y.Z` и пересоберите.

### Inno Setup не найден
Установите Inno Setup 6 или поправьте путь `ISCC.exe` в `build_windows.ps1`
(`$IsccPath`) / `build_windows.bat` (`ISCC_PATH`).

### Переключение языков не работает (в собранном или dev-приложении)
Не скомпилированы `.mo`. Выполните Шаг 2
(`python -m babel.messages.frontend compile -d translations`) и перезапустите.

### `ProxyError` / `No matching distribution found` при установке зависимостей
См. `docs/WINDOWS_PROXY_TROUBLESHOOTING.md`.

### PowerShell не запускает `venv\Scripts\python.exe`
Используйте префикс `.\`: `.\venv\Scripts\python.exe tools\update_version.py status`.

## Связанные документы

- `README.md`
- `VERSION_MANAGEMENT.md`
- `docs/release_guide.md`
- `docs/WINDOWS_PROXY_TROUBLESHOOTING.md`
