@echo off
REM Setup script for VPN Server Manager on Windows
REM Version is read from config/config.json.template

echo ========================================
echo VPN Server Manager - Windows Setup
echo ========================================
echo.
echo NOTE: This process may take 3-5 minutes
echo Please wait while we:
echo   - Create virtual environment
echo   - Download and install dependencies
echo   - Configure your application
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.13+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment...
REM Check if venv exists AND is valid (has activate.bat)
if exist venv\Scripts\activate.bat (
    echo [INFO] Virtual environment already exists
) else (
    REM Remove broken venv folder if it exists
    if exist venv (
        echo [INFO] Removing broken virtual environment...
        rmdir /s /q venv
    )
    
    echo [INFO] Creating new virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)
echo.

echo [2/4] Activating virtual environment...
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment python not found
    echo [INFO] Try deleting the venv folder and run this script again
    pause
    exit /b 1
)
echo [OK] Virtual environment is ready
echo.

echo [3/5] Installing dependencies...
echo This may take 3-5 minutes, please wait...
echo If your internet is slow, pip retries and extended timeouts will be used.
echo.
set PIP_INSTALL_CMD=venv\Scripts\python.exe -m pip install -r requirements.txt --progress-bar on --timeout 120 --retries 10 --prefer-binary
echo Running: %PIP_INSTALL_CMD%
%PIP_INSTALL_CMD%
if errorlevel 1 (
    echo [WARNING] First attempt failed, retrying once...
    echo.
    %PIP_INSTALL_CMD%
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        echo [INFO] If the error mentions timeout or proxy, see docs\WINDOWS_PROXY_TROUBLESHOOTING.md
        pause
        exit /b 1
    )
)
echo.
echo [OK] Dependencies installed
echo.

echo [4/5] Generating encryption key...
python generate_key.py
if errorlevel 1 (
    echo [ERROR] Failed to generate encryption key
    pause
    exit /b 1
)
echo.

echo [5/5] Creating config file...
if not exist config.json (
    if exist config\config.json.template (
        copy config\config.json.template config.json >nul
        echo [OK] Config file created from template
    ) else (
        echo [ERROR] config\config.json.template not found!
        pause
        exit /b 1
    )
) else (
    echo [INFO] Config file already exists
)
echo.

echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo To start the application:
echo   - Desktop mode: start_windows.bat
echo   - Or manually:  venv\Scripts\python.exe run_desktop.py
echo.
pause

