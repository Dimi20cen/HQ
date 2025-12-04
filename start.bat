@echo off
:: %~dp0 tells the script to look in "This Current Folder"
cd /d "%~dp0"

:: Use the python inside your virtual environment to run the app
.venv\Scripts\python.exe run.py

:: Keep window open if it crashes so you can see the error
pause