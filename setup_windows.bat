@echo off
REM Setup script for VPN Server Manager on Windows
REM VPN Server Manager v4.0.8

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
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment...
if not exist venv (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [INFO] Virtual environment already exists
)
echo.

echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

echo [3/5] Installing dependencies...
echo This may take 3-5 minutes, please wait...
echo.
pip install -r requirements.txt --progress-bar on
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
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
    if exist config.json.example (
        copy config.json.example config.json >nul
        echo [OK] Config file created from config.json.example
    ) else (
        echo [WARNING] config.json.example not found
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
echo   - Or manually:  venv\Scripts\activate ^&^& python run.py --desktop
echo.
pause

