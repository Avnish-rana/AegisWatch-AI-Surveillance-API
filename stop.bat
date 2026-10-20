@echo off
title AegisWatch — Stop
echo Stopping AegisWatch...
:: Kill any uvicorn/python processes on port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000"') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo Done. AegisWatch stopped.
timeout /t 2 >nul
