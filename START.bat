@echo off
title LoanIQ Website
color 0A
cls

echo.
echo  ==========================================
echo    LoanIQ - Loan Approval Website
echo  ==========================================
echo.

set PROJECT=C:\Users\pbharatsonkusare\Desktop\Project\LoanWebsite

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found. Install from python.org
    pause & exit /b 1
)

cd /d "%PROJECT%"

:: Create venv if not exists
if not exist ".venv" (
    echo  Creating virtual environment...
    python -m venv .venv
)

:: Install flask
echo  Installing Flask...
.venv\Scripts\pip install flask --quiet

:: Run
echo.
echo  Starting website...
echo  Open your browser and go to: http://127.0.0.1:5000
echo.
echo  Press Ctrl+C to stop.
echo  ==========================================
echo.

start "" "http://127.0.0.1:5000"
.venv\Scripts\python app.py

pause
