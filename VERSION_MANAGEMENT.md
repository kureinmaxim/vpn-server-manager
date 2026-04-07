# Управление версиями VPN Server Manager

Этот документ описывает, как в проекте `VPN Server Manager` хранится версия приложения, как её безопасно менять и какие файлы синхронизируются автоматически.

Связанные документы:
- `BUILD.md` — сборка приложения и инсталлятора
- `docs/release_guide.md` — общий релизный процесс
- `CHANGELOG.md` — история изменений

---

## Источник правды

Единственный источник правды для версии релиза:
- `config.json`

Ключевые поля:

```json
{
  "app_info": {
    "version": "4.1.1",
    "release_date": "08.12.2025",
    "last_updated": "2025-12-08"
  }
}
```

Важно:
- версия релиза не должна задаваться из пользовательских конфигов в `%APPDATA%`, `~/Library/Application Support` или других локальных каталогах
- пользовательский `config.json`, создаваемый при первом запуске упакованного приложения, нужен для runtime-настроек, но не является источником версии репозитория
- если версия меняется для релиза, меняем её через `tools/update_version.py`, а не вручную по файлам

---

## Что синхронизируется автоматически

После изменения версии скрипт синхронизирует производные файлы:
- `config/config.json.template`
- `README.md`
- `vpn-manager-installer.iss`
- `env.example`
- `app/config.py`
- `app/__init__.py`
- `setup.py`

Это нужно, чтобы:
- UI показывал правильную версию
- Windows-инсталлятор собирался с правильным номером
- шаблонный конфиг для новых установок не отставал
- fallback-значения в коде не расходились с реальным релизом

---

## Основной CLI

Главный инструмент:
- `tools/update_version.py`

Совместимый старый wrapper:
- `tools/bump_version.py`

### Команды

```text
python tools/update_version.py status
python tools/update_version.py sync
python tools/update_version.py sync X.Y.Z
python tools/update_version.py bump patch
python tools/update_version.py bump minor
python tools/update_version.py bump major
```

### Что делают команды

- `status` — показывает текущую версию из `config.json` и проверяет рассинхрон по отслеживаемым файлам
- `sync` — приводит производные файлы к версии из `config.json`
- `sync X.Y.Z` — ставит конкретную версию в `config.json` и синхронизирует все производные файлы
- `bump patch|minor|major` — увеличивает семантическую версию и синхронизирует проект

### Дополнительные флаги

```text
--release-date DD.MM.YYYY
--last-updated YYYY-MM-DD
--dry-run
```

По умолчанию:
- `sync` без новой версии сохраняет текущие даты из `config.json`
- `sync X.Y.Z` и `bump ...` ставят сегодняшние даты, если они не переданы явно

---

## Примеры

### Windows

```powershell
venv\Scripts\python.exe tools\update_version.py status
venv\Scripts\python.exe tools\update_version.py sync
venv\Scripts\python.exe tools\update_version.py sync 4.1.2
venv\Scripts\python.exe tools\update_version.py bump patch
```

Если используется `.venv`:

```powershell
.venv\Scripts\python.exe tools\update_version.py status
```

### macOS / Linux

```bash
venv/bin/python3 tools/update_version.py status
venv/bin/python3 tools/update_version.py sync
venv/bin/python3 tools/update_version.py bump patch
```

### Совместимый старый скрипт

```powershell
venv\Scripts\python.exe tools\bump_version.py --bump patch
venv\Scripts\python.exe tools\bump_version.py --version 4.1.2
```

---

## Рекомендуемый workflow

### Проверить состояние перед релизом

```powershell
venv\Scripts\python.exe tools\update_version.py status
```

### Поднять patch-версию

```powershell
venv\Scripts\python.exe tools\update_version.py bump patch
```

### Поставить точную версию вручную

```powershell
venv\Scripts\python.exe tools\update_version.py sync 4.2.0
```

### После изменения версии

Сделайте минимум следующее:
1. Обновите `CHANGELOG.md`
2. Проверьте `tools/update_version.py status`
3. Соберите приложение/инсталлятор
4. Проверьте, что UI и имя инсталлятора показывают ту же версию

---

## Как это связано со сборкой

Сборочные сценарии читают версию из:
- `config.json`

Это касается:
- `build_windows.bat`
- `build_windows.ps1`
- `build_macos.py`
- `setup.py`

То есть перед сборкой не нужно отдельно менять номер версии в нескольких местах: достаточно использовать `tools/update_version.py`.

---

## Что не является источником версии

Не используем как источник правды:
- `%APPDATA%\VPNServerManager-Clean\config.json`
- `~/Library/Application Support/VPNServerManager-Clean/config.json`
- переменную окружения `APP_VERSION`
- имя уже собранного `.exe` или `.dmg`

Причина простая:
- эти данные могут относиться к старой локальной установке
- они не должны “откатывать” или “подменять” версию релиза в репозитории

---

## Troubleshooting

### `status` показывает рассинхрон

Запустите:

```powershell
venv\Scripts\python.exe tools\update_version.py sync
```

### В UI одна версия, а в инсталляторе другая

Проверьте:
- `config.json`
- `vpn-manager-installer.iss`
- `README.md`
- вывод `tools/update_version.py status`

Обычно проблема означает, что версия была изменена вручную только в одном месте.

### После первого запуска упакованного приложения в `%APPDATA%` другая версия

Проверьте, что сборка выполнялась после синхронизации версии. Пользовательский конфиг создаётся из данных сборки и не должен редактироваться как релизный источник правды.

---

## Коротко

Для этого проекта правило такое:
- меняем версию через `tools/update_version.py`
- храним источник правды в `config.json`
- не используем пользовательские runtime-конфиги как источник версии
- перед релизом всегда проверяем `status`

