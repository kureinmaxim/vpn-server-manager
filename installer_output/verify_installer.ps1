# Автоматическая проверка контрольной суммы инсталлятора
# VPN Server Manager v4.0.7

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Проверка подлинности инсталлятора" -ForegroundColor Cyan
Write-Host "VPN Server Manager v4.0.8" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$InstallerFile = "VPN-Server-Manager-Setup-v4.0.8.exe"
$ChecksumFile = "checksum.txt"

# Проверяем наличие файлов
Write-Host "Проверка наличия файлов..." -ForegroundColor Yellow

if (-not (Test-Path $InstallerFile)) {
    Write-Host ""
    Write-Host "ОШИБКА: Файл $InstallerFile не найден!" -ForegroundColor Red
    Write-Host "Убедитесь, что скрипт находится в той же папке с инсталлятором." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

if (-not (Test-Path $ChecksumFile)) {
    Write-Host ""
    Write-Host "ОШИБКА: Файл $ChecksumFile не найден!" -ForegroundColor Red
    Write-Host "Скачайте checksum.txt с официальной страницы релиза." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host "✓ Все файлы найдены" -ForegroundColor Green
Write-Host ""

# Читаем ожидаемую контрольную сумму
Write-Host "Чтение официальной контрольной суммы..." -ForegroundColor Yellow
$ExpectedHash = Get-Content $ChecksumFile -Raw | ForEach-Object { $_.Trim() }
Write-Host "✓ Загружено: $ExpectedHash" -ForegroundColor Green
Write-Host ""

# Вычисляем контрольную сумму файла
Write-Host "Вычисление контрольной суммы инсталлятора..." -ForegroundColor Yellow
Write-Host "(это может занять несколько секунд)" -ForegroundColor Gray
$ActualHash = (Get-FileHash $InstallerFile -Algorithm SHA256).Hash
Write-Host "✓ Вычислено: $ActualHash" -ForegroundColor Green
Write-Host ""

# Сравниваем
Write-Host "Сравнение контрольных сумм..." -ForegroundColor Yellow
Write-Host ""

if ($ExpectedHash -eq $ActualHash) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✓ ПРОВЕРКА УСПЕШНА!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Файл подлинный и не поврежден." -ForegroundColor Green
    Write-Host "Можно безопасно устанавливать." -ForegroundColor Green
    Write-Host ""
    
    # Показываем дополнительную информацию
    $FileInfo = Get-Item $InstallerFile
    Write-Host "Информация о файле:" -ForegroundColor Cyan
    Write-Host "  Имя:    $($FileInfo.Name)" -ForegroundColor White
    Write-Host "  Размер: $([math]::Round($FileInfo.Length / 1MB, 2)) МБ" -ForegroundColor White
    Write-Host "  Дата:   $($FileInfo.LastWriteTime)" -ForegroundColor White
    Write-Host ""
    
    # Предлагаем запустить установку
    $Response = Read-Host "Запустить установку сейчас? (Y/N)"
    if ($Response -eq 'Y' -or $Response -eq 'y') {
        Write-Host ""
        Write-Host "Запуск инсталлятора..." -ForegroundColor Cyan
        Start-Process -FilePath $InstallerFile
    } else {
        Write-Host ""
        Write-Host "Установка отменена." -ForegroundColor Yellow
    }
    
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "✗ ПРОВЕРКА НЕ ПРОЙДЕНА!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "ВНИМАНИЕ: Файл поврежден или подделан!" -ForegroundColor Red
    Write-Host "НЕ УСТАНАВЛИВАЙТЕ ЭТОТ ФАЙЛ!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Ожидалось:" -ForegroundColor Yellow
    Write-Host "  $ExpectedHash" -ForegroundColor White
    Write-Host ""
    Write-Host "Получено:" -ForegroundColor Yellow
    Write-Host "  $ActualHash" -ForegroundColor White
    Write-Host ""
    Write-Host "Рекомендации:" -ForegroundColor Cyan
    Write-Host "  1. Удалите этот файл" -ForegroundColor White
    Write-Host "  2. Очистите кэш браузера" -ForegroundColor White
    Write-Host "  3. Скачайте заново с официального сайта" -ForegroundColor White
    Write-Host "  4. Проверьте снова" -ForegroundColor White
    Write-Host ""
}

Write-Host ""
Write-Host "Документация: CHECKSUM_GUIDE.md" -ForegroundColor Gray
Write-Host "Поддержка: github.com/kureinmaxim/vpn-server-manager/issues" -ForegroundColor Gray
Write-Host ""
Read-Host "Нажмите Enter для выхода"

