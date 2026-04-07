# VPN Server Manager - Windows Setup (PowerShell)
# Version 4.0.7

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VPN Server Manager - Windows Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NOTE: This process may take 3-5 minutes" -ForegroundColor Yellow
Write-Host "Please wait while we:" -ForegroundColor White
Write-Host "  - Create virtual environment" -ForegroundColor Gray
Write-Host "  - Download and install dependencies" -ForegroundColor Gray
Write-Host "  - Configure your application" -ForegroundColor Gray
Write-Host ""

# [1/5] Check Python
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow

try {
    $pythonVersion = & python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python 3.8+ from https://www.python.org/" -ForegroundColor White
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

# [2/5] Create virtual environment
Write-Host "[2/5] Creating virtual environment..." -ForegroundColor Yellow

if (-not (Test-Path "venv")) {
    try {
        & python -m venv venv
        Write-Host "[OK] Virtual environment created" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Failed to create virtual environment" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "[INFO] Virtual environment already exists" -ForegroundColor Cyan
}
Write-Host ""

# [3/5] Activate and install dependencies
Write-Host "[3/5] Installing dependencies..." -ForegroundColor Yellow
Write-Host "This may take 3-5 minutes, please wait..." -ForegroundColor Cyan
Write-Host ""

try {
    & .\venv\Scripts\Activate.ps1
    & pip install -r requirements.txt --progress-bar on
    Write-Host ""
    Write-Host "[OK] Dependencies installed" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "[ERROR] Failed to install dependencies" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

# [4/5] Generate encryption key
Write-Host "[4/5] Generating encryption key..." -ForegroundColor Yellow

try {
    & python generate_key.py
    Write-Host ""
} catch {
    Write-Host "[ERROR] Failed to generate encryption key" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# [5/5] Create config file
Write-Host "[5/5] Creating config file..." -ForegroundColor Yellow

if (-not (Test-Path "config.json")) {
    if (Test-Path "config.json.example") {
        Copy-Item "config.json.example" "config.json"
        Write-Host "[OK] Config file created from config.json.example" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] config.json.example not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "[INFO] Config file already exists" -ForegroundColor Cyan
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "Setup completed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start the application:" -ForegroundColor White
Write-Host "  - Desktop mode: .\start_windows.bat" -ForegroundColor Cyan
Write-Host "  - Or manually:  .\venv\Scripts\Activate.ps1; python run.py --desktop" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to exit"

