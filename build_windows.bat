@echo off
REM Automatic builder for VPN Server Manager Windows Installer
REM VPN Server Manager v4.0.7
REM Uses Inno Setup Compiler to create installer

echo ========================================
echo VPN Server Manager - Installer Builder
echo ========================================
echo.

REM Проверяем версию
set APP_VERSION=4.0.9
echo Building installer for version %APP_VERSION%
echo.

REM Путь к Inno Setup Compiler (стандартная установка)
set ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe

REM Проверяем, установлен ли Inno Setup
if not exist "%ISCC_PATH%" (
    echo [ERROR] Inno Setup Compiler not found!
    echo.
    echo Please install Inno Setup 6 from:
    echo https://jrsoftware.org/isdl.php
    echo.
    echo Or update ISCC_PATH in this script if installed elsewhere.
    pause
    exit /b 1
)

echo [1/5] Checking Inno Setup Compiler...
echo Found: %ISCC_PATH%
echo.

REM Проверяем наличие скрипта Inno Setup
if not exist "vpn-manager-installer.iss" (
    echo [ERROR] File vpn-manager-installer.iss not found!
    echo.
    echo Please run this script from the project root directory.
    pause
    exit /b 1
)

echo [2/5] Checking project files...

REM Проверяем критически важные файлы
set FILES_OK=1

if not exist "LICENSE" (
    echo [WARNING] LICENSE file not found
    set FILES_OK=0
)

if not exist "README_WINDOWS.md" (
    echo [WARNING] README_WINDOWS.md not found
    set FILES_OK=0
)

if not exist "static\favicon.ico" (
    echo [WARNING] static\favicon.ico not found
    set FILES_OK=0
)

if not exist "config.json.example" (
    echo [WARNING] config.json.example not found
    set FILES_OK=0
)

if not exist "env.example" (
    echo [WARNING] env.example not found
    set FILES_OK=0
)

if %FILES_OK%==0 (
    echo.
    echo [WARNING] Some files are missing. Continue anyway? (Y/N)
    choice /C YN /N
    if errorlevel 2 exit /b 1
)

echo [OK] Required files found
echo.

REM Проверяем, что секретные файлы НЕ включены
echo [3/5] Security check...

set SECURITY_WARNING=0

if exist ".env" (
    echo [WARNING] .env file exists! It will NOT be included in installer.
    set SECURITY_WARNING=1
)

if exist "config.json" (
    echo [WARNING] config.json file exists! It will NOT be included in installer.
    set SECURITY_WARNING=1
)

if exist "data\*.enc" (
    echo [WARNING] Encrypted data files exist! They will NOT be included in installer.
    set SECURITY_WARNING=1
)

if %SECURITY_WARNING%==0 (
    echo [OK] No sensitive files found
) else (
    echo.
    echo NOTE: Sensitive files are excluded from installer by design.
)
echo.

REM Очистка перед сборкой
echo [4/5] Cleaning up before build...

REM Удаляем старое виртуальное окружение если есть
if exist "venv" (
    echo Removing old venv directory...
    rmdir /s /q venv 2>nul
)

REM Удаляем Python кеш
echo Removing Python cache...
del /s /q *.pyc 2>nul
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul

REM Удаляем логи
if exist "logs" (
    echo Removing logs directory...
    rmdir /s /q logs 2>nul
)

REM Создаем папку для вывода если её нет
if not exist "installer_output" (
    mkdir installer_output
)

echo [OK] Cleanup completed
echo.

REM Компиляция инсталлятора
echo [5/5] Building installer...
echo.
echo Running Inno Setup Compiler...
echo ----------------------------------------

"%ISCC_PATH%" "vpn-manager-installer.iss"

if errorlevel 1 (
    echo.
    echo ========================================
    echo [ERROR] Build failed!
    echo ========================================
    echo.
    echo Check the error messages above.
    pause
    exit /b 1
)

echo ----------------------------------------
echo.

REM Проверяем результат
set OUTPUT_FILE=installer_output\VPN-Server-Manager-Setup-v%APP_VERSION%.exe

if exist "%OUTPUT_FILE%" (
    echo ========================================
    echo [SUCCESS] Build completed!
    echo ========================================
    echo.
    echo Installer created:
    echo %OUTPUT_FILE%
    echo.
    
    REM Получаем размер файла
    for %%A in ("%OUTPUT_FILE%") do set FILE_SIZE=%%~zA
    echo File size: %FILE_SIZE% bytes
    echo.
    
    REM Создаем контрольную сумму SHA-256
    echo Creating SHA-256 checksum...
    powershell -Command "Get-FileHash '%OUTPUT_FILE%' -Algorithm SHA256 | Select-Object -ExpandProperty Hash" > installer_output\checksum.txt
    
    if exist "installer_output\checksum.txt" (
        echo.
        echo SHA-256:
        type installer_output\checksum.txt
        echo.
    )
    
    REM Показываем следующие шаги
    echo ========================================
    echo Next steps:
    echo ========================================
    echo.
    echo 1. Test the installer:
    echo    - Run %OUTPUT_FILE%
    echo    - Test installation on clean system
    echo    - Test uninstallation
    echo.
    echo 2. Create release notes:
    echo    - Update CHANGELOG.md
    echo    - Prepare GitHub release description
    echo.
    echo 3. Distribute:
    echo    - Upload to GitHub Releases
    echo    - Include checksum.txt
    echo    - Update download links
    echo.
    echo 4. Documentation:
    echo    - See WINDOWS_INSTALLER_GUIDE.md
    echo.
    
    REM Опционально: открыть папку с результатом
    echo Press any key to open output folder...
    pause >nul
    explorer installer_output
    
) else (
    echo ========================================
    echo [ERROR] Installer not found!
    echo ========================================
    echo.
    echo Expected file: %OUTPUT_FILE%
    echo.
    echo The build may have failed silently.
    echo Check the Inno Setup output above for errors.
    pause
    exit /b 1
)

echo.
echo Build process completed!
echo.
pause

