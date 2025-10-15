# VPN Server Manager - Windows Installer Builder (PowerShell)
# Version 4.0.9

# Настройки
$ErrorActionPreference = "Stop"
$AppVersion = "4.0.9"
$IsccPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

# Цвета для вывода
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VPN Server Manager - Installer Builder" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Building installer for version $AppVersion" -ForegroundColor White
Write-Host ""

# [1/5] Проверка Inno Setup Compiler
Write-Host "[1/5] Checking Inno Setup Compiler..." -ForegroundColor Yellow

if (-not (Test-Path $IsccPath)) {
    Write-Host "[ERROR] Inno Setup Compiler not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Inno Setup 6 from:" -ForegroundColor White
    Write-Host "https://jrsoftware.org/isdl.php" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Or update `$IsccPath in this script if installed elsewhere." -ForegroundColor White
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Found: $IsccPath" -ForegroundColor Green
Write-Host ""

# Проверка скрипта Inno Setup
if (-not (Test-Path "vpn-manager-installer.iss")) {
    Write-Host "[ERROR] File vpn-manager-installer.iss not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run this script from the project root directory." -ForegroundColor White
    Read-Host "Press Enter to exit"
    exit 1
}

# [2/5] Проверка файлов проекта
Write-Host "[2/5] Checking project files..." -ForegroundColor Yellow

$RequiredFiles = @(
    "LICENSE",
    "README_WINDOWS.md",
    "static\favicon.ico",
    "config.json.example",
    "env.example"
)

$FilesOk = $true

foreach ($file in $RequiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Host "[WARNING] $file not found" -ForegroundColor Yellow
        $FilesOk = $false
    }
}

if (-not $FilesOk) {
    Write-Host ""
    $response = Read-Host "[WARNING] Some files are missing. Continue anyway? (Y/N)"
    if ($response -ne "Y" -and $response -ne "y") {
        exit 1
    }
}

Write-Host "[OK] Required files found" -ForegroundColor Green
Write-Host ""

# [3/5] Проверка безопасности
Write-Host "[3/5] Security check..." -ForegroundColor Yellow

$SecurityWarning = $false

if (Test-Path ".env") {
    Write-Host "[WARNING] .env file exists! It will NOT be included in installer." -ForegroundColor Yellow
    $SecurityWarning = $true
}

if (Test-Path "config.json") {
    Write-Host "[WARNING] config.json file exists! It will NOT be included in installer." -ForegroundColor Yellow
    $SecurityWarning = $true
}

if (Test-Path "data\*.enc") {
    Write-Host "[WARNING] Encrypted data files exist! They will NOT be included in installer." -ForegroundColor Yellow
    $SecurityWarning = $true
}

if (-not $SecurityWarning) {
    Write-Host "[OK] No sensitive files found" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "NOTE: Sensitive files are excluded from installer by design." -ForegroundColor Cyan
}
Write-Host ""

# [4/5] Очистка перед сборкой
Write-Host "[4/5] Cleaning up before build..." -ForegroundColor Yellow

# Удаляем виртуальное окружение
if (Test-Path "venv") {
    Write-Host "Removing old venv directory..." -ForegroundColor White
    Remove-Item -Path "venv" -Recurse -Force -ErrorAction SilentlyContinue
}

# Удаляем Python кеш
Write-Host "Removing Python cache..." -ForegroundColor White
Get-ChildItem -Path . -Include "*.pyc" -Recurse -Force | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Include "__pycache__" -Recurse -Force -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Удаляем логи
if (Test-Path "logs") {
    Write-Host "Removing logs directory..." -ForegroundColor White
    Remove-Item -Path "logs" -Recurse -Force -ErrorAction SilentlyContinue
}

# Создаем папку для вывода
if (-not (Test-Path "installer_output")) {
    New-Item -ItemType Directory -Path "installer_output" | Out-Null
}

Write-Host "[OK] Cleanup completed" -ForegroundColor Green
Write-Host ""

# [5/5] Компиляция инсталлятора
Write-Host "[5/5] Building installer..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Running Inno Setup Compiler..." -ForegroundColor White
Write-Host "----------------------------------------" -ForegroundColor Gray

try {
    # Запускаем компиляцию
    $process = Start-Process -FilePath $IsccPath -ArgumentList "vpn-manager-installer.iss" -NoNewWindow -Wait -PassThru
    
    if ($process.ExitCode -ne 0) {
        throw "Compilation failed with exit code $($process.ExitCode)"
    }
    
    Write-Host "----------------------------------------" -ForegroundColor Gray
    Write-Host ""
    
    # Проверяем результат
    $OutputFile = "installer_output\VPN-Server-Manager-Setup-v$AppVersion.exe"
    
    if (Test-Path $OutputFile) {
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "[SUCCESS] Build completed!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        
        Write-Host "Installer created:" -ForegroundColor White
        Write-Host $OutputFile -ForegroundColor Cyan
        Write-Host ""
        
        # Размер файла
        $FileSize = (Get-Item $OutputFile).Length
        Write-Host "File size: $FileSize bytes ($([math]::Round($FileSize/1MB, 2)) MB)" -ForegroundColor White
        Write-Host ""
        
        # Создаем контрольную сумму SHA-256
        Write-Host "Creating SHA-256 checksum..." -ForegroundColor White
        $Hash = Get-FileHash -Path $OutputFile -Algorithm SHA256
        $Hash.Hash | Out-File -FilePath "installer_output\checksum.txt" -Encoding ASCII
        
        Write-Host ""
        Write-Host "SHA-256:" -ForegroundColor White
        Write-Host $Hash.Hash -ForegroundColor Cyan
        Write-Host ""
        
        # Следующие шаги
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "1. Test the installer:" -ForegroundColor White
        Write-Host "   - Run $OutputFile" -ForegroundColor Gray
        Write-Host "   - Test installation on clean system" -ForegroundColor Gray
        Write-Host "   - Test uninstallation" -ForegroundColor Gray
        Write-Host ""
        Write-Host "2. Create release notes:" -ForegroundColor White
        Write-Host "   - Update CHANGELOG.md" -ForegroundColor Gray
        Write-Host "   - Prepare GitHub release description" -ForegroundColor Gray
        Write-Host ""
        Write-Host "3. Distribute:" -ForegroundColor White
        Write-Host "   - Upload to GitHub Releases" -ForegroundColor Gray
        Write-Host "   - Include checksum.txt" -ForegroundColor Gray
        Write-Host "   - Update download links" -ForegroundColor Gray
        Write-Host ""
        Write-Host "4. Documentation:" -ForegroundColor White
        Write-Host "   - See WINDOWS_INSTALLER_GUIDE.md" -ForegroundColor Gray
        Write-Host ""
        
        # Открываем папку с результатом
        Write-Host "Opening output folder..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        Invoke-Item "installer_output"
        
    } else {
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "[ERROR] Installer not found!" -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "Expected file: $OutputFile" -ForegroundColor White
        Write-Host ""
        Write-Host "The build may have failed silently." -ForegroundColor Yellow
        Write-Host "Check the Inno Setup output above for errors." -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
    
} catch {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "[ERROR] Build failed!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check the error messages above." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "Build process completed!" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"

