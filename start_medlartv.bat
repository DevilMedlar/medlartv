@echo off
REM MedlarTV Launcher - Fixed for Windows
REM This version includes Ollama startup and better error handling

color 0B
title MedlarTV Launcher

echo.
echo ================================================================
echo.
echo    MEDLARTV - Tactical AI System
echo.
echo ================================================================
echo.

REM Create logs directory
if not exist "logs" mkdir logs

REM Check if .env exists
if not exist ".env" (
    color 0C
    echo [ERROR] .env file not found!
    echo.
    pause
    exit /b 1
)

REM Check if Ollama is installed
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Ollama is not installed or not in PATH!
    echo.
    echo Install from: https://ollama.ai
    echo.
    pause
    exit /b 1
)

echo [CHECK] Starting Ollama server...
echo.

REM Start Ollama serve in background
start "Ollama Server" /min cmd /c "ollama serve > logs\ollama.log 2>&1"
timeout /t 3 /nobreak >nul

REM Check if Ollama is responding
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Ollama may not be ready yet, waiting...
    timeout /t 5 /nobreak >nul
)

echo [OK] Ollama server started
echo.

REM Start Core API
echo [START] Core API (FastAPI)...
start "MedlarTV Core" cmd /c "python MedlarTV\core\main.py > logs\core.log 2>&1"
timeout /t 4 /nobreak >nul

REM Check if Core started (look for the process)
tasklist /FI "WindowTitle eq MedlarTV Core*" 2>nul | find /i "cmd.exe" >nul
if %errorlevel% neq 0 (
    color 0C
    echo [FAIL] Core API failed to start!
    echo.
    echo Check logs\core.log for details
    echo.
    type logs\core.log
    echo.
    pause
    exit /b 1
)
echo [OK] Core API started
echo.

REM Start WebSocket Bridge
echo [START] WebSocket Bridge...
start "MedlarTV Bridge" cmd /c "python MedlarTV\avatar\bridge.py > logs\bridge.log 2>&1"
timeout /t 3 /nobreak >nul

REM Check if Bridge started
tasklist /FI "WindowTitle eq MedlarTV Bridge*" 2>nul | find /i "cmd.exe" >nul
if %errorlevel% neq 0 (
    color 0C
    echo [FAIL] Bridge failed to start!
    echo.
    echo Stopping Core API...
    taskkill /FI "WindowTitle eq MedlarTV Core*" /F >nul 2>&1
    echo.
    echo Check logs\bridge.log for details
    echo.
    pause
    exit /b 1
)
echo [OK] Bridge started
echo.

REM Start Twitch Listener
echo [START] Twitch Listener...
start "MedlarTV Twitch" cmd /c "python MedlarTV\tools\twitch_listener.py"
timeout /t 3 /nobreak >nul

REM Check if Twitch started
tasklist /FI "WindowTitle eq MedlarTV Twitch*" 2>nul | find /i "cmd.exe" >nul
if %errorlevel% neq 0 (
    color 0C
    echo [FAIL] Twitch Listener failed to start!
    echo.
    echo Stopping other components...
    taskkill /FI "WindowTitle eq MedlarTV*" /F >nul 2>&1
    echo.
    pause
    exit /b 1
)
echo [OK] Twitch Listener started
echo.

color 0A
echo ================================================================
echo.
echo    MedlarTV Systems Operational
echo.
echo ================================================================
echo.
echo Active Components:
echo   - Ollama Server (background)
echo   - Core API (FastAPI)
echo   - WebSocket Bridge
echo   - Twitch Listener
echo.
echo Windows:
echo   - Check "Ollama Server" window for Ollama logs
echo   - Check "MedlarTV Core" window for API logs
echo   - Check "MedlarTV Bridge" window for Bridge logs
echo   - Check "MedlarTV Twitch" window for bot logs
echo.
echo Logs saved to: logs\ directory
echo.
echo To stop: Close this window or run stop_medlartv.bat
echo.
pause