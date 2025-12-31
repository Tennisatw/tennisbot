@echo off
setlocal EnableExtensions EnableDelayedExpansion

set STOP_CODE=95
set MAX_RESTARTS=20
set WINDOW_SECONDS=60

set RESTART_COUNT=0
set WINDOW_START=%TIME%

:loop
uv run main.py

set EXIT_CODE=%ERRORLEVEL%

if "%EXIT_CODE%"=="%STOP_CODE%" (
  echo [start.bat] Stop code %STOP_CODE% detected, stopping with exit code 0.
  exit /b 0
)

for /f "tokens=1-4 delims=:." %%a in ("%TIME%") do set /a NOW_S=%%a*3600+%%b*60+%%c
for /f "tokens=1-4 delims=:." %%a in ("%WINDOW_START%") do set /a START_S=%%a*3600+%%b*60+%%c

set /a ELAPSED=NOW_S-START_S
if !ELAPSED! lss 0 set /a ELAPSED+=86400

if !ELAPSED! geq %WINDOW_SECONDS% (
  set RESTART_COUNT=0
  set WINDOW_START=%TIME%
)

set /a RESTART_COUNT+=1
if !RESTART_COUNT! geq %MAX_RESTARTS% (
  set "RC=!RESTART_COUNT!"
  echo [start.bat] Too many restarts in %WINDOW_SECONDS%s, stopping.
  exit /b %STOP_CODE%
)

echo [start.bat] Restart code %EXIT_CODE% detected, restarting...
timeout /t 1 /nobreak >nul
goto loop
