# Проверка установленной версии VPN Server Manager

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Проверка установленной версии" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Проверяем через реестр
$uninstallPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

$vpnApps = foreach ($path in $uninstallPaths) {
    Get-ItemProperty $path -ErrorAction SilentlyContinue | 
    Where-Object { $_.DisplayName -like "*VPN Server Manager*" }
}

if ($vpnApps) {
    foreach ($app in $vpnApps) {
        Write-Host "Найдено:" -ForegroundColor Yellow
        Write-Host "  Название: $($app.DisplayName)" -ForegroundColor White
        Write-Host "  Версия:   $($app.DisplayVersion)" -ForegroundColor White
        Write-Host "  Издатель: $($app.Publisher)" -ForegroundColor White
        Write-Host "  Путь:     $($app.InstallLocation)" -ForegroundColor White
        Write-Host ""
    }
    
    # Проверяем количество
    $count = @($vpnApps).Count
    if ($count -gt 1) {
        Write-Host "ВНИМАНИЕ: Найдено $count версий!" -ForegroundColor Red
        Write-Host "Удалите старые версии через appwiz.cpl" -ForegroundColor Yellow
    } else {
        Write-Host "✓ Установлена только одна версия" -ForegroundColor Green
    }
} else {
    Write-Host "❌ VPN Server Manager не найден" -ForegroundColor Red
}

Write-Host "`n========================================`n" -ForegroundColor Cyan

# Проверяем ярлык
$desktopPath = [Environment]::GetFolderPath('Desktop')
$shortcut = "$desktopPath\VPN Server Manager.lnk"

if (Test-Path $shortcut) {
    Write-Host "Ярлык на рабочем столе:" -ForegroundColor Yellow
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($shortcut)
    Write-Host "  Путь: $($link.TargetPath)" -ForegroundColor White
    Write-Host ""
    
    if ($link.TargetPath -like "*3.5.9*") {
        Write-Host "❌ ОШИБКА: Ярлык указывает на старую версию!" -ForegroundColor Red
    } elseif ($link.TargetPath -like "*4.0.8*" -or $link.TargetPath -like "*start_windows.bat*") {
        Write-Host "✓ Ярлык указывает на новую версию" -ForegroundColor Green
    }
} else {
    Write-Host "❌ Ярлык на рабочем столе не найден" -ForegroundColor Red
}

Write-Host ""
Read-Host "Нажмите Enter для выхода"

