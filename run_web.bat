@echo off
echo ===================================================
echo   THE SILENT INVIGILATOR - LAUNCHER
echo ===================================================
echo.
echo [INFO] Activating Virtual Environment...
call .venv\Scripts\activate

echo [INFO] Starting Web Dashboard (app.py)...
echo [INFO] Please open http://127.0.0.1:5000 in your browser
echo.
cd backend
python app.py
pause
