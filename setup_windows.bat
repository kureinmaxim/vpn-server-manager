@echo off
REM Setup script for VPN Server Manager on Windows
REM VPN Server Manager v4.0.5

echo ========================================
echo VPN Server Manager - Windows Setup
echo ========================================
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

echo [3/4] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

echo [4/4] Generating encryption key...
python generate_key.py
if errorlevel 1 (
    echo [ERROR] Failed to generate encryption key
    pause
    exit /b 1
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

