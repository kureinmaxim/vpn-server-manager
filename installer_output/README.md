# VPN Server Manager v4.2.2 - Инсталлятор для Windows

## Что в этой папке

| Файл | Описание |
|------|----------|
| `VPN-Server-Manager-Setup-v4.2.2.exe` | Основной Windows-инсталлятор |
| `checksum.txt` | SHA-256 хэш для проверки целостности |

## Быстрая проверка

### PowerShell

```powershell
Get-FileHash -Path "VPN-Server-Manager-Setup-v4.2.2.exe" -Algorithm SHA256
```

Ожидаемый SHA-256:

```text
04CE419DF03257DB789D96DEE2B690B0DD4295CFA22076A9AD623F457621B524
```

### CMD

```cmd
certutil -hashfile "VPN-Server-Manager-Setup-v4.2.2.exe" SHA256
```

## Установка

1. Запустите `VPN-Server-Manager-Setup-v4.2.2.exe`.
2. При необходимости используйте запуск от имени администратора.
3. После установки приложение появится в `%LOCALAPPDATA%\Programs\VPN Server Manager`.

## Размер файла

```text
6,564,406 bytes
```

## Связанные документы

- `CHECKSUMS.md`
- `../BUILD.md`
- `../docs/CHECKSUM_GUIDE.md`
