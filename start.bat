@echo off
setlocal enabledelayedexpansion

REM Gmail Chat Application Setup and Start Script (Windows Batch)
REM This script sets up the environment and starts both the API and Streamlit UI

echo ==========================================
echo 📧 Gmail Chat Application Setup ^& Start
echo ==========================================

REM Check if Python is installed
echo [INFO] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH. Please install Python 3.8+ first.
    pause
    exit /b 1
)
echo [SUCCESS] Python found: 
python --version

REM Check if uv is installed
echo [INFO] Checking uv installation...
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] uv is not installed. Please install uv first.
    echo You can install it with: pip install uv
    pause
    exit /b 1
)
echo [SUCCESS] uv found: 
uv --version

REM Install dependencies using uv
echo [INFO] Installing dependencies using uv...
if exist "requirements.txt" (
    echo [INFO] Installing main requirements...
    uv pip install -r requirements.txt
)
if exist "agent_builder_client\requirements.txt" (
    echo [INFO] Installing agent_builder_client requirements...
    uv pip install -r agent_builder_client\requirements.txt
)
echo [SUCCESS] All dependencies installed using uv

REM Check if required files exist
echo [INFO] Checking required files...
if not exist "agent_builder_client\api.py" (
    echo [ERROR] Missing required file: agent_builder_client\api.py
    pause
    exit /b 1
)
if not exist "streamlit_chat_ui.py" (
    echo [ERROR] Missing required file: streamlit_chat_ui.py
    pause
    exit /b 1
)
if not exist "agent_builder_client\config.py" (
    echo [ERROR] Missing required file: agent_builder_client\config.py
    pause
    exit /b 1
)
echo [SUCCESS] All required files found

REM Check if credentials.json exists
echo [INFO] Checking Google OAuth2 credentials...
if not exist "credentials.json" (
    echo [WARNING] credentials.json not found
    echo [WARNING] Please download your Google OAuth2 credentials and save as 'credentials.json'
    echo [WARNING] You can continue without it, but Gmail fetching will not work
) else (
    echo [SUCCESS] Google OAuth2 credentials found
)

REM Check if multilingual-e5-large model exists
echo [INFO] Checking embedding model...
if not exist "multilingual-e5-large" (
    echo [WARNING] multilingual-e5-large model directory not found
    echo [WARNING] Please download the model first:
    echo [WARNING] git clone https://huggingface.co/intfloat/multilingual-e5-large
    echo [WARNING] You can continue without it, but the API may not work properly
) else (
    echo [SUCCESS] Embedding model found
)

echo.
echo ==========================================
echo 🚀 Starting Services...
echo ==========================================

REM Start API service
echo [INFO] Starting FastAPI service...
cd agent_builder_client
start "FastAPI Service" cmd /k "uv run api.py"
cd ..
echo [SUCCESS] FastAPI service started in new window

REM Wait a bit for the API to start
timeout /t 3 /nobreak >nul

REM Start Streamlit UI
echo [INFO] Starting Streamlit UI...
start "Streamlit UI" cmd /k "uv run streamlit run streamlit_chat_ui.py --server.headless true"
echo [SUCCESS] Streamlit UI started in new window

echo.
echo ==========================================
echo ✅ Setup Complete!
echo ==========================================
echo.
echo 🌐 Services are now running:
echo    📡 FastAPI: http://localhost:8080
echo    🖥️  Streamlit UI: http://localhost:8501 (default port)
echo.
echo 📋 API Endpoints:
echo    - Health Check: http://localhost:8080/health
echo    - API Docs: http://localhost:8080/docs
echo    - Create DB: http://localhost:8080/create_db
echo    - Query: http://localhost:8080/query_group
echo.
echo 📖 For more information, check the README.md file
echo.
echo Press any key to exit...
pause >nul
