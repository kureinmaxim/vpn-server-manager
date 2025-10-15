@echo off
REM Start script for VPN Server Manager on Windows
REM VPN Server Manager v4.0.5

echo ========================================
echo VPN Server Manager v4.0.5
echo ========================================
echo.

REM Check if virtual environment exists
if not exist venv (
    echo [ERROR] Virtual environment not found!
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

REM Check if .env exists
if not exist .env (
    echo [WARNING] .env file not found!
    echo Creating from env.example and generating key...
    echo.
    call venv\Scripts\activate.bat
    python generate_key.py
    echo.
)

REM Check if config.json exists
if not exist config.json (
    echo [WARNING] config.json file not found!
    if exist config.json.example (
        echo Creating from config.json.example...
        copy config.json.example config.json >nul
        echo [OK] Config file created
    ) else (
        echo [ERROR] config.json.example not found!
        pause
        exit /b 1
    )
    echo.
)

REM Activate virtual environment and start application
echo Starting application in Desktop mode...
echo.
call venv\Scripts\activate.bat && python run.py --desktop

if errorlevel 1 (
    echo.
    echo [ERROR] Application failed to start
    pause
    exit /b 1
)

