# Руководство по сборке и релизу VPN Server Manager

Это актуальный релизный процесс для `VPN Server Manager`.

Связанные документы:

- `VERSION_MANAGEMENT.md`
- `BUILD.md`
- `CHANGELOG.md`

## 1. Перед релизом

Убедитесь, что:

- рабочее дерево чистое или вы понимаете все локальные изменения;
- установлен GitHub CLI, если релиз публикуется через `gh`;
- зависимости проекта установлены;
- версия синхронизируется через `tools/update_version.py`.

### Windows PowerShell

Если `venv` уже создан:

```powershell
.\venv\Scripts\python.exe tools\update_version.py status
```

Если `venv` ещё нет:

```powershell
python tools\update_version.py status
```

### macOS / Linux

```bash
venv/bin/python3 tools/update_version.py status
```

Если используется `.venv`, замените путь соответственно.

## 2. Обновление версии

Источник правды:

- `config/config.json.template`

Менять версию вручную в нескольких файлах не нужно.

### Поднять patch-версию

```text
python tools/update_version.py bump patch
```

### Поднять minor-версию

```text
python tools/update_version.py bump minor
```

### Поставить конкретную версию

```text
python tools/update_version.py sync 4.2.3
```

### Проверить итог

```text
python tools/update_version.py status
```

После этого автоматически синхронизируются:

- `config/config.json.template`
- `README.md`
- `vpn-manager-installer.iss`
- `env.example`
- `app/config.py`
- `app/__init__.py`
- `setup.py`

## 3. Обновление CHANGELOG

После `bump` или `sync` обновите `CHANGELOG.md`.

Рекомендуемый формат:

```markdown
## [4.2.3] - 2026-04-07

### Added
- ...

### Changed
- ...

### Fixed
- ...
```

Если в проекте используется более подробный стиль, сохраняйте его, но версия в заголовке должна совпадать с релизной версией из `config/config.json.template`.

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

PowerShell:

```powershell
.\build_windows.ps1
```

или CMD:

```cmd
build_windows.bat
```

Ожидаемый артефакт:

- `installer_output/VPN-Server-Manager-Setup-vX.Y.Z.exe`

Важно:

- сборщики читают релизную версию из `config/config.json.template`;
- перед сборкой не нужно вручную править `vpn-manager-installer.iss`.

## 5. Проверка собранного релиза

Минимум проверьте:

- приложение запускается;
- версия в UI совпадает с версией релиза;
- вход по PIN работает;
- имя `.exe` или `.dmg` совпадает с номером релиза.

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

## 6. Коммит релизных изменений

После обновления версии, `CHANGELOG.md` и сборки:

```bash
git add config/config.json.template README.md env.example app/config.py app/__init__.py setup.py vpn-manager-installer.iss CHANGELOG.md
git commit -m "chore(release): vX.Y.Z"
git push origin main
```

Если релиз затрагивает документацию или дополнительные артефакты, добавьте их явно.

## 7. Создание git-тега

### macOS / Linux

```bash
VERSION=$(jq -r .app_info.version config/config.json.template)
TAG=v$VERSION
git tag -a "$TAG" -m "Release $VERSION"
git push origin "$TAG"
```

### Windows PowerShell

```powershell
$version = (Get-Content "config/config.json.template" -Raw | ConvertFrom-Json).app_info.version
$tag = "v$version"
git tag -a $tag -m "Release $version"
git push origin $tag
```

## 8. Создание релиза на GitHub

### Через GitHub CLI

#### macOS / Linux

```bash
VERSION=$(jq -r .app_info.version config/config.json.template)
TAG=v$VERSION

gh release create "$TAG" \
  --title "VPN Server Manager v$VERSION" \
  --notes-file CHANGELOG.md \
  dist/VPNServerManager-Clean_Installer.dmg
```

#### Windows PowerShell

```powershell
$version = (Get-Content "config/config.json.template" -Raw | ConvertFrom-Json).app_info.version
$tag = "v$version"

gh release create $tag `
  --title "VPN Server Manager v$version" `
  --notes-file CHANGELOG.md `
  "installer_output/VPN-Server-Manager-Setup-v$version.exe"
```

Если нужно опубликовать оба артефакта, приложите и `.exe`, и `.dmg`.

## 9. SHA256 и публикация контрольных сумм

Пример для Windows PowerShell:

```powershell
Get-FileHash "installer_output\VPN-Server-Manager-Setup-vX.Y.Z.exe" -Algorithm SHA256
```

Подробности см. в `docs/CHECKSUM_GUIDE.md`.

## 10. Итоговый чеклист

- `python tools/update_version.py status` показывает синхрон;
- `CHANGELOG.md` обновлён;
- сборка Windows и/или macOS завершилась успешно;
- имя артефактов совпадает с релизной версией;
- git tag создан и отправлен;
- релиз опубликован на GitHub.
