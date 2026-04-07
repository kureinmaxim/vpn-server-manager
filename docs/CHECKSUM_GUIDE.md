# Руководство по контрольным суммам SHA-256

Этот документ описывает актуальный минимальный процесс создания и проверки SHA-256 для релизных артефактов.

Важно:

- используйте реальные имена артефактов текущего релиза, а не старые примерные версии;
- вместо жёстко прошитых `v4.0.x` подставляйте текущую версию сборки.

## Что проверять

Обычно проверяется:

- `installer_output/VPN-Server-Manager-Setup-vX.Y.Z.exe`
- `dist/VPNServerManager-Clean_Installer.dmg`

## Создание SHA-256

### Windows PowerShell

```powershell
Get-FileHash "installer_output\VPN-Server-Manager-Setup-vX.Y.Z.exe" -Algorithm SHA256
```

Сохранить только hash в файл:

```powershell
Get-FileHash "installer_output\VPN-Server-Manager-Setup-vX.Y.Z.exe" -Algorithm SHA256 |
  Select-Object -ExpandProperty Hash |
  Out-File -FilePath "installer_output\checksum.txt" -Encoding ASCII
```

### Windows CMD

```cmd
certutil -hashfile "installer_output\VPN-Server-Manager-Setup-vX.Y.Z.exe" SHA256
```

### macOS / Linux

```bash
shasum -a 256 "dist/VPNServerManager-Clean_Installer.dmg"
```

## Проверка

Сравните опубликованную сумму с суммой локально скачанного файла.

Если значения различаются:

- файл повреждён;
- загружен не тот артефакт;
- сборка не соответствует опубликованному релизу.

## Встраивание в релизный процесс

Перед публикацией релиза:

1. Соберите артефакты.
2. Проверьте версию через `python tools/update_version.py status`.
3. Посчитайте SHA-256 для каждого публикуемого файла.
4. Опубликуйте checksum рядом с релизом.

Подробный релизный сценарий:

- `release_guide.md`
- `../BUILD.md`
