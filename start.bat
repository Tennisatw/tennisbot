@echo off
setlocal enabledelayedexpansion

:loop
uv run main.py
set EXIT_CODE=%ERRORLEVEL%

if "%EXIT_CODE%"=="-1" (
  echo [start.bat] Exit code -1 detected, restarting...
  timeout /t 1 /nobreak >nul
  goto loop
)

echo [start.bat] Program exited with code %EXIT_CODE%, stopping.
exit /b %EXIT_CODE%
