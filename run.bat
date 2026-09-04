@echo off
title EventPulse - Event Management System
echo ====================================================
echo Starting EventPulse Event Operations Platform...
echo ====================================================
python -m pip install -r requirements.txt
python -c "import sample_data; sample_data.seed_sample_data()"
echo.
echo Launching server at http://127.0.0.1:8000
echo Press Ctrl+C in this window to stop the server.
echo.
python main.py
pause
