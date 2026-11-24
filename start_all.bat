@echo off
echo ===================================================
echo     Starting IndoClip Pro (Full-Stack 0 Budget)
echo ===================================================
start "IndoClip Backend (FastAPI)" cmd /c "%~dp0run_backend.bat"
start "IndoClip Frontend (Next.js)" cmd /c "%~dp0run_frontend.bat"
echo.
echo Kedua server sedang dibuka di terminal terpisah!
echo Buka browser Anda di: http://localhost:3000
echo.
timeout /t 5
start http://localhost:3000
