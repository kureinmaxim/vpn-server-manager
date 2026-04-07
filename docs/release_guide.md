# Руководство по сборке и релизу VPN Server Manager

Это актуальный релизный процесс для `VPN Server Manager` после перехода на централизованное управление версиями через `config.json` и `tools/update_version.py`.

Связанные документы:
- `VERSION_MANAGEMENT.md` — правила хранения и синхронизации версий
- `BUILD.md` — общая инструкция по сборке
- `CHANGELOG.md` — история изменений

## 1. Перед релизом

Убедитесь, что:
- рабочее дерево чистое или вы понимаете все локальные изменения
- установлен GitHub CLI, если релиз создаётся через `gh`
- есть рабочее окружение Python с зависимостями проекта
- сборка выполняется после синхронизации версии

### Windows

```powershell
venv\Scripts\python.exe tools\update_version.py status
```

### macOS / Linux

```bash
venv/bin/python3 tools/update_version.py status
```

Если используется `.venv`, замените путь на `.venv`.

---

## 2. Обновление версии

Источник правды:
- `config.json`

Менять версию вручную в нескольких файлах больше не нужно. Для этого используется `tools/update_version.py`.

### Поднять patch-версию

```powershell
venv\Scripts\python.exe tools\update_version.py bump patch
```

### Поднять minor-версию

```powershell
venv\Scripts\python.exe tools\update_version.py bump minor
```

### Поставить конкретную версию

```powershell
venv\Scripts\python.exe tools\update_version.py sync 4.1.2
```

### Проверить итог

```powershell
venv\Scripts\python.exe tools\update_version.py status
```

После этого автоматически синхронизируются:
- `config/config.json.template`
- `README.md`
- `vpn-manager-installer.iss`
- `env.example`
- `app/config.py`
- `app/__init__.py`
- `setup.py`

---

## 3. Обновление CHANGELOG

После bump/sync обновите `CHANGELOG.md`.

Рекомендуемый формат:

```markdown
## [4.1.2] - 2026-04-06

### Added
- ...

### Changed
- ...

### Fixed
- ...
```

Если в проекте уже используется более подробный формат с эмодзи и подзаголовками, сохраняйте его стиль, но версия в заголовке должна совпадать с `config.json`.

---

## 4. Сборка релизных артефактов

### macOS

```bash
source venv/bin/activate
python3 build_macos.py
```

Ожидаемые артефакты:
- `dist/VPNServerManager-Clean.app`
- `dist/VPNServerManager-Clean_Installer.dmg`

### Windows

```powershell
venv\Scripts\python.exe tools\update_version.py status
.\build_windows.ps1
```

или

```powershell
build_windows.bat
```

Ожидаемый артефакт:
- `installer_output/VPN-Server-Manager-Setup-vX.Y.Z.exe`

Важно:
- Windows-сборщики теперь читают версию из `config.json`
- перед сборкой не нужно отдельно править `vpn-manager-installer.iss`

---

## 5. Проверка собранного релиза

Минимум проверьте:
- приложение запускается
- версия в UI совпадает с версией релиза
- вход по PIN работает
- основные страницы открываются
- Windows `.exe` или macOS `.dmg` действительно собраны с нужной версией в имени файла

### Быстрая проверка macOS `.app`

```bash
/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" \
  dist/VPNServerManager-Clean.app/Contents/Info.plist
```

### Быстрая проверка Windows-инсталлятора

Проверьте имя файла в `installer_output/`:

```text
VPN-Server-Manager-Setup-vX.Y.Z.exe
```

---

## 6. Коммит релизных изменений

После обновления версии, `CHANGELOG.md` и сборки:

```bash
git add config.json config/config.json.template README.md env.example app/config.py app/__init__.py setup.py vpn-manager-installer.iss CHANGELOG.md
git commit -m "chore(release): vX.Y.Z"
git push origin main
```

Если в релиз входят ещё артефакты или документация, добавьте их явно.

---

## 7. Создание git-тега

### macOS / Linux

```bash
VERSION=$(jq -r .app_info.version config.json)
TAG=v$VERSION
git tag -a "$TAG" -m "Release $VERSION"
git push origin "$TAG"
```

### Windows PowerShell

```powershell
$version = (Get-Content "config.json" -Raw | ConvertFrom-Json).app_info.version
$tag = "v$version"
git tag -a $tag -m "Release $version"
git push origin $tag
```

---

## 8. Создание релиза на GitHub

### Через GitHub CLI

#### macOS / Linux

```bash
VERSION=$(jq -r .app_info.version config.json)
TAG=v$VERSION

gh release create "$TAG" \
  --title "VPN Server Manager v$VERSION" \
  --notes-file CHANGELOG.md \
  dist/VPNServerManager-Clean_Installer.dmg
```

#### Windows PowerShell

```powershell
$version = (Get-Content "config.json" -Raw | ConvertFrom-Json).app_info.version
$tag = "v$version"

gh release create $tag `
  --title "VPN Server Manager v$version" `
  --notes-file CHANGELOG.md `
  "installer_output/VPN-Server-Manager-Setup-v$version.exe"
```

Если нужно опубликовать оба артефакта, укажите и `.exe`, и `.dmg`, когда они доступны.

### Через веб-интерфейс GitHub

1. Откройте страницу репозитория.
2. Перейдите в `Releases`.
3. Нажмите `Draft a new release`.
4. Выберите тег `vX.Y.Z`.
5. Заголовок: `VPN Server Manager vX.Y.Z`.
6. В описание вставьте итог из `CHANGELOG.md`.
7. Прикрепите релизные файлы.
8. Опубликуйте релиз.

---

## 9. SHA256 и публикация контрольных сумм

### macOS

```bash
shasum -a 256 "dist/VPNServerManager-Clean_Installer.dmg"
```

### Windows PowerShell

```powershell
Get-FileHash "installer_output\VPN-Server-Manager-Setup-vX.Y.Z.exe" -Algorithm SHA256
```

Если контрольные суммы публикуются в релизе, добавьте их в описание GitHub Release или обновите файл в `installer_output/`, если это часть вашего workflow.

---

## 10. Короткий release checklist

1. `tools/update_version.py status`
2. `tools/update_version.py bump patch` или `sync X.Y.Z`
3. Обновить `CHANGELOG.md`
4. Снова выполнить `tools/update_version.py status`
5. Собрать нужные артефакты
6. Проверить версию в UI и в именах файлов
7. Закоммитить изменения
8. Создать тег `vX.Y.Z`
9. Создать GitHub Release
10. Проверить, что релиз отображается как ожидается

---

## 11. Частые проблемы

### Версия в UI и инсталляторе отличается

Почти всегда это значит, что версия была изменена вручную, а не через `tools/update_version.py`.

Решение:

```powershell
venv\Scripts\python.exe tools\update_version.py status
venv\Scripts\python.exe tools\update_version.py sync
```

### Тег уже существует

```bash
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z
```

Делайте это только если уверены, что тег нужно пересоздать.

### GitHub Release создан без артефактов

Проверьте:
- существуют ли файлы в `dist/` или `installer_output/`
- совпадает ли версия в имени артефакта с версией тега
- запускается ли команда `gh release create` из корня проекта

---

## 12. Полезные команды

### Проверить текущую версию

```bash
python tools/update_version.py status
```

### Проверить версию напрямую из `config.json`

```bash
jq -r .app_info.version config.json
```

### Windows PowerShell

```powershell
(Get-Content "config.json" -Raw | ConvertFrom-Json).app_info.version
```
