@echo off
REM MedlarTV Launcher Script for Windows
REM Usage: start_medlartv.bat

color 0B
echo.
echo ================================================================
echo.
echo    MEDLARTV - Tactical AI System
echo.
echo ================================================================
echo.

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Check if .env exists
if not exist ".env" (
    color 0C
    echo [ERROR] .env file not found!
    pause
    exit /b 1
)

echo [START] Launching MedlarTV components...
echo.

REM Start Core API
echo [START] Core API ^(FastAPI^)...
start "MedlarTV Core" /min python MedlarTV/core/main.py
timeout /t 3 /nobreak >nul
echo [OK] Core API started
echo.

REM Start WebSocket Bridge
echo [START] WebSocket Bridge...
start "MedlarTV Bridge" /min python MedlarTV/avatar/bridge.py
timeout /t 2 /nobreak >nul
echo [OK] Bridge started
echo.

REM Start Twitch Listener
echo [START] Twitch Listener...
start "MedlarTV Twitch" python MedlarTV/tools/twitch_listener.py
timeout /t 2 /nobreak >nul
echo [OK] Twitch Listener started
echo.

echo ================================================================
echo.
echo    MedlarTV Systems Operational
echo.
echo ================================================================
echo.
echo Active Components:
echo   - Core API
echo   - WebSocket Bridge
echo   - Twitch Listener
echo.
echo Check individual windows for component status
echo Close this window to keep MedlarTV running
echo.
pause