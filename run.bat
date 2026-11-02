@echo off
title E.D.I.T.H. Desktop Interface
echo ====================================================
echo Starting E.D.I.T.H. Desktop Interface...
echo ====================================================
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] An error occurred while launching E.D.I.T.H.
    echo [!] Make sure Python is in your PATH and dependencies are installed:
    echo     pip install -r requirements.txt
    pause
)
