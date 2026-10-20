@echo off
:: AegisWatch — Windows Startup Script
:: Launches the AegisWatch backend and opens the dashboard in your default browser.
:: Safe: only kills the specific uvicorn process started by this script.

setlocal EnableDelayedExpansion

title AegisWatch — AI Surveillance System

:: ── Configuration ────────────────────────────────────────────────────────────
set PORT=8000
set HOST=0.0.0.0
set LOG_LEVEL=warning

:: ── Resolve script directory ─────────────────────────────────────────────────
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo.
echo  ===================================================
echo   AegisWatch — AI Surveillance System
echo  ===================================================
echo   Project : %SCRIPT_DIR%
echo   URL     : http://localhost:%PORT%
echo  ===================================================
echo.

:: ── Check Python ─────────────────────────────────────────────────────────────
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.9+ and add it to PATH.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] %PYVER%

:: ── Check / create uploads and evidence directories ──────────────────────────
if not exist "data\uploads"  mkdir "data\uploads"
if not exist "data\evidence" mkdir "data\evidence"
if not exist "data\videos\demo" mkdir "data\videos\demo"

:: ── Seed the database if it does not exist ───────────────────────────────────
if not exist "surveillance.db" (
    echo [INFO] Database not found — running first-time seed...
    python database\seed\seed_data.py
    if %ERRORLEVEL% neq 0 (
        echo [WARN] Seed script reported an error — continuing anyway.
    ) else (
        echo [OK] Database seeded.
    )
) else (
    echo [OK] Database already exists — skipping seed.
)

:: ── Check that uvicorn is available ──────────────────────────────────────────
python -c "import uvicorn" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] uvicorn not installed. Run:  pip install -r requirements.txt
    pause
    exit /b 1
)

:: ── Start the server ─────────────────────────────────────────────────────────
echo.
echo [INFO] Starting AegisWatch server on http://localhost:%PORT% ...
echo [INFO] Press Ctrl+C to stop.
echo.

:: Open browser after a short delay (2 seconds)
start "" /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:%PORT%"

:: Launch uvicorn (blocking — this window stays open while the server runs)
python -m uvicorn backend.src.main:app --host %HOST% --port %PORT% --log-level %LOG_LEVEL%

echo.
echo [INFO] Server stopped.
pause
