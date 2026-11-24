@echo off
echo ===================================================
echo     IndoClip Pro - Backend Server (FastAPI)
echo ===================================================
cd /d "%~dp0backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app
pause
