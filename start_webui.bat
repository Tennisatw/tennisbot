@echo off
setlocal EnableExtensions

REM Start Tennisbot Web UI (dev)
REM - Backend: FastAPI (uvicorn) on http://0.0.0.0:8000
REM - Frontend: Vite dev server on http://0.0.0.0:5173

cd /d %~dp0

start "tennisbot-web-backend" cmd /k "uv run python -m uvicorn web.backend.app:app --host 0.0.0.0 --port 8000"
start "tennisbot-web-frontend" cmd /k "cd web\frontend && pnpm install && pnpm dev"
start "tennisbot-web-browser" "https://10.0.0.31:5173/"

echo [start_web.bat] Started.
exit /b 0
