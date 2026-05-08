@echo off
title Exam Generator

echo ========================================
echo    Exam Generator - Starting
echo ========================================
echo.
echo [*] Starting server, please wait...
echo [*] First launch may take a while to load models
echo [*] Browser will open automatically
echo.
echo [*] Press Ctrl+C to stop
echo.

set PYTHONPATH=%~dp0
set API_PORT=8080
python\python.exe main.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Start failed, error code: %errorlevel%
    echo [!] Make sure python\ folder exists and deps are installed
    echo [!] Or run setup_portable.bat to rebuild environment
    echo.
)

pause
