@echo off
REM Stop all MedlarTV processes

echo Stopping MedlarTV...

taskkill /FI "WindowTitle eq MedlarTV Core*" /F >nul 2>&1
taskkill /FI "WindowTitle eq MedlarTV Bridge*" /F >nul 2>&1
taskkill /FI "WindowTitle eq MedlarTV Twitch*" /F >nul 2>&1

echo All MedlarTV processes stopped.
pause