@echo off
echo ===================================================
echo   THE SILENT INVIGILATOR - STANDALONE MODE
echo ===================================================
echo.
echo [INFO] Activating Virtual Environment...
call .venv\Scripts\activate

echo [INFO] Starting Silent Invigilator Desktop App...
echo.
cd backend
python silent_invigilator.py
pause
