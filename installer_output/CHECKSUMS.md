# Контрольные суммы - VPN Server Manager v4.2.2

## Основной инсталлятор

**Файл:** `VPN-Server-Manager-Setup-v4.2.2.exe`  
**Размер:** `6,564,406 bytes`  
**SHA-256:** `04CE419DF03257DB789D96DEE2B690B0DD4295CFA22076A9AD623F457621B524`

## Проверка в PowerShell

```powershell
Get-FileHash -Path "VPN-Server-Manager-Setup-v4.2.2.exe" -Algorithm SHA256
```

Ожидаемый вывод:

```text
Algorithm : SHA256
Hash      : 04CE419DF03257DB789D96DEE2B690B0DD4295CFA22076A9AD623F457621B524
```

## Проверка в CMD

```cmd
certutil -hashfile "VPN-Server-Manager-Setup-v4.2.2.exe" SHA256
```

## Если checksum не совпадает

- не устанавливайте файл;
- скачайте артефакт заново;
- сравните SHA-256 ещё раз.

## Связанные документы

- `README.md`
- `../docs/CHECKSUM_GUIDE.md`
