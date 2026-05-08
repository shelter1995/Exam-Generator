@echo off
title Setup Portable Environment

echo ========================================
echo    Exam Generator - Environment Setup
echo ========================================
echo.
echo This script will:
echo   1. Download embedded Python 3.11
echo   2. Install pip
echo   3. Install all dependencies
echo.
echo First-time setup downloads ~1-2GB, please wait
echo.

pause

set PYTHON_VERSION=3.11.9
set PYTHON_EMBED_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip
set GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py
set PYTHON_DIR=python

if exist "%PYTHON_DIR%\python.exe" (
    echo [*] Found python\python.exe, skipping download
    goto :install_deps
)

echo [1/4] Downloading Python %PYTHON_VERSION%...
curl -L -o python-embed.zip "%PYTHON_EMBED_URL%"
if %errorlevel% neq 0 (
    echo [!] Download failed, check network
    echo [!] Manual download: %PYTHON_EMBED_URL%
    echo [!] Save as python-embed.zip in this folder and retry
    pause
    exit /b 1
)

echo [2/4] Extracting Python...
mkdir "%PYTHON_DIR%"
tar -xf python-embed.zip -C "%PYTHON_DIR%"
del python-embed.zip

echo [*] Enabling site-packages...
powershell -Command "(Get-Content '%PYTHON_DIR%\python311._pth') -replace '#import site', 'import site' | Set-Content '%PYTHON_DIR%\python311._pth'"

echo [3/4] Installing pip...
curl -L -o get-pip.py "%GET_PIP_URL%"
"%PYTHON_DIR%\python.exe" get-pip.py
del get-pip.py

:install_deps
echo [4/4] Installing dependencies...
echo [*] This may take a while...
"%PYTHON_DIR%\python.exe" -m pip install --upgrade pip
"%PYTHON_DIR%\python.exe" -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [!] Dependency install failed, check network or requirements.txt
    pause
    exit /b 1
)

echo.
echo ========================================
echo    Setup Complete!
echo ========================================
echo.
echo To start: double-click start.bat
echo To distribute: zip the entire folder
echo.

pause
