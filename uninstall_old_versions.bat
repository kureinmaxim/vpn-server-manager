@echo off
REM Uninstall older VPN Server Manager builds
REM Uninstall the listed entries in Windows first (Apps & features)

echo ========================================
echo Uninstall old VPN Server Manager versions
echo ========================================
echo.
echo WARNING: This removes ALL VPN Server Manager app installs.
echo Your data (.env, config.json, data/) is kept.
echo.
pause

echo.
echo Opening Apps ^& features...
appwiz.cpl

echo.
echo ========================================
echo Steps
echo ========================================
echo.
echo 1. Find "VPN Server Manager 3.5.9"
echo 2. Click Uninstall
echo 3. Choose to keep data if asked
echo.
echo 4. Find "VPN Server Manager, version 4.0.8"
echo 5. Click Uninstall
echo 6. Choose to keep data if asked
echo.
echo 7. After both are gone, press any key here
echo.
pause

echo.
echo Checking leftover folders...
echo.

if exist "C:\Program Files\VPN Server Manager" (
    echo FOUND: C:\Program Files\VPN Server Manager
    echo Removing...
    rd /s /q "C:\Program Files\VPN Server Manager"
)

if exist "C:\Users\%USERNAME%\AppData\Local\Programs\VPN Server Manager" (
    echo FOUND: C:\Users\%USERNAME%\AppData\Local\Programs\VPN Server Manager
    echo Leaving it — it may contain user data
)

echo.
echo Removing old shortcuts...
del "%USERPROFILE%\Desktop\VPN Server Manager.lnk" 2>nul
REM Russian Windows OneDrive desktop folder name
del "%USERPROFILE%\OneDrive\Рабочий стол\VPN Server Manager.lnk" 2>nul

echo.
echo ========================================
echo Done. Install the new version next.
echo ========================================
echo.
pause
