@echo off
REM MedlarTV Launcher - Windows (PYTHONPATH Fixed)
title MedlarTV Launcher

color 0B

echo.
echo ================================================================
echo.
echo    MEDLARTV - Tactical AI System
echo.
echo ================================================================
echo.

REM Create logs directory
if not exist "logs" mkdir logs

REM Check .env
if not exist ".env" (
    color 0C
    echo [ERROR] .env file not found!
    pause
    exit /b 1
)

REM Start Ollama
echo [CHECK] Starting Ollama server...
start "Ollama Server" /min cmd /c "ollama serve > logs\ollama.log 2>&1"
timeout /t 3 /nobreak >nul
echo [OK] Ollama started
echo.

REM Start Core API (with PYTHONPATH set)
echo [START] Core API (FastAPI)...
start "MedlarTV Core" cmd /k "cd /d %CD% && set PYTHONPATH=%CD% && python MedlarTV\core\main.py"
timeout /t 5 /nobreak >nul
echo [OK] Core API started
echo.

REM Start Bridge (with PYTHONPATH set)
echo [START] WebSocket Bridge...
start "MedlarTV Bridge" cmd /k "cd /d %CD% && set PYTHONPATH=%CD% && python MedlarTV\avatar\bridge.py"
timeout /t 3 /nobreak >nul
echo [OK] Bridge started
echo.

REM Start Twitch Bot (with PYTHONPATH set)
echo [START] Twitch Listener...
start "MedlarTV Twitch" cmd /k "cd /d %CD% && set PYTHONPATH=%CD% && python MedlarTV\tools\twitch_listener.py"
timeout /t 3 /nobreak >nul
echo [OK] Twitch Listener started
echo.

color 0A
echo ================================================================
echo.
echo    MedlarTV Systems Operational
echo.
echo ================================================================
echo.
echo Active Windows:
echo   - Ollama Server (minimized)
echo   - MedlarTV Core (FastAPI)
echo   - MedlarTV Bridge (WebSocket)
echo   - MedlarTV Twitch (Bot)
echo.
echo Close individual windows to stop components
echo Or run stop_medlartv.bat to stop all
echo.
echo This window can be closed safely
echo.
pause