@echo off
title AegisWatch — Setup
color 0A
echo.
echo  ╔═══════════════════════════════════════════════════╗
echo  ║   AegisWatch AI Surveillance — First-Time Setup   ║
echo  ╚═══════════════════════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ from python.org
    pause
    exit /b 1
)

echo [1/5] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
) else (
    echo       Virtual environment already exists - skipping
)

echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/5] Installing dependencies (this may take several minutes)...
pip install --upgrade pip --quiet
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed. Check requirements.txt and your internet connection.
    pause
    exit /b 1
)

echo [4/5] Creating .env configuration...
if not exist ".env" (
    copy .env.example .env >nul 2>&1
    echo       Created .env from .env.example
) else (
    echo       .env already exists - skipping
)

echo [5/5] Initializing database and seeding demo data...
python database\seed\seed_data.py
if errorlevel 1 (
    echo [WARNING] Seed may have failed or data already exists. Continuing...
)

echo.
echo  ✅ Setup complete!
echo.
echo  To start the application:  start.bat
echo  Default URL:               http://localhost:8000
echo  Login:                     admin / admin123
echo.
pause
