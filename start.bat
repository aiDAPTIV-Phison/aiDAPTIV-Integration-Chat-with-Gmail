@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ==========================================
REM Gmail Chat Application Launcher (Advanced)
REM ==========================================

REM Get script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Set encoding environment variable
set PYTHONIOENCODING=utf-8

echo ==========================================
echo Gmail Chat Application Launcher
echo ==========================================
echo.
echo Current directory: %CD%
echo.

REM Check if Python is installed
echo [INFO] Checking Python...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo [INFO] Please install Python 3.8+ first
    echo.
    pause
    exit /b 1
)
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] Found: !PYTHON_VERSION!
) else (
    echo [WARNING] Could not get Python version
)
echo.

REM Check if uv is installed
echo [INFO] Checking uv...
where uv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] uv is not installed or not in PATH
    echo [INFO] Attempting to install uv...
    python -m pip install uv >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install uv automatically
        echo [INFO] Please install uv manually: pip install uv
        echo.
        pause
        exit /b 1
    )
    echo [OK] uv installed successfully
) else (
    for /f "tokens=*" %%i in ('uv --version 2^>^&1') do set UV_VERSION=%%i
    echo [OK] Found: !UV_VERSION!
)
echo.

REM Check and download embedding model
echo [INFO] Checking embedding model...
set TARGET_DIR=multilingual-e5-large

REM Skip if directory already exists
if exist "%TARGET_DIR%" (
    echo [OK] Directory "%TARGET_DIR%" already exists, skipping download.
) else (
    echo [INFO] Model directory not found, starting download...
    echo [INFO] Downloading multilingual-e5-large model from Hugging Face...
    echo [INFO] This may take some time, please wait...
    echo.
    
    REM Check if git is installed
    where git >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] git is not installed or not in PATH
        echo [WARNING] Cannot download model automatically, please download manually:
        echo [WARNING] git clone https://huggingface.co/intfloat/multilingual-e5-large
        echo [WARNING] Or download manually from https://huggingface.co/intfloat/multilingual-e5-large
        echo.
    ) else (
        REM Execute clone
        git clone https://huggingface.co/intfloat/multilingual-e5-large "%TARGET_DIR%"
        if errorlevel 1 (
            echo [ERROR] Clone failed, please check network or permissions.
            echo [WARNING] Application may not work properly, but you can continue to start.
            echo.
        ) else (
            echo [OK] Clone completed, content located at "%TARGET_DIR%".
        )
    )
)
echo.

REM Check if build_exe.py exists
if not exist "build_exe.py" (
    echo [ERROR] build_exe.py not found in current directory
    echo [INFO] Current directory: %CD%
    echo.
    pause
    exit /b 1
)
echo [OK] Found build_exe.py
echo.

REM Check and install dependencies (ensure virtual environment exists)
echo [INFO] Ensuring virtual environment and dependencies...
if not exist ".venv" (
    echo [INFO] Virtual environment not found, creating...
    uv venv --python 3.12.11 .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] Failed to create virtual environment with uv
        echo [INFO] Trying with standard venv...
        python -m venv .venv
        if %ERRORLEVEL% NEQ 0 (
            echo [ERROR] Failed to create virtual environment
            pause
            exit /b 1
        )
    )
    echo [OK] Virtual environment created
)

REM Install dependencies
set REQ_FILE=requirements_all.txt
if not exist "%REQ_FILE%" (
    set REQ_FILE=requirements.txt
)

if exist "%REQ_FILE%" (
    echo [INFO] Installing dependencies from %REQ_FILE%...
    echo [INFO] This may take a few minutes, please wait...
    echo.
    uv pip install -r "%REQ_FILE%"
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] uv pip install failed, trying with pip...
        if exist ".venv\Scripts\pip.exe" (
            .venv\Scripts\pip.exe install -r "%REQ_FILE%"
        ) else (
            python -m pip install -r "%REQ_FILE%"
        )
        if %ERRORLEVEL% NEQ 0 (
            echo [ERROR] Failed to install dependencies
            echo [INFO] Please check the error messages above
            echo [INFO] You can try manually: pip install -r %REQ_FILE%
            echo.
            pause
            exit /b 1
        ) else (
            echo [OK] Dependencies installed using pip
        )
    ) else (
        echo [OK] Dependencies installed using uv
    )
) else (
    echo [WARNING] No requirements file found (%REQ_FILE%)
    echo [INFO] Skipping dependency installation...
)
echo.

REM Run build_exe.py using uv run
echo ==========================================
echo Starting application...
echo ==========================================
echo.

uv run build_exe.py

REM Check execution result
set EXIT_CODE=%ERRORLEVEL%
if %EXIT_CODE% NEQ 0 (
    echo.
    echo ==========================================
    echo [ERROR] Application exited with error code: %EXIT_CODE%
    echo ==========================================
    echo.
    pause
    exit /b %EXIT_CODE%
)

echo.
echo ==========================================
echo Application closed normally
echo ==========================================
pause


