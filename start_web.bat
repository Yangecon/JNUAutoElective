@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo JNUAutoElective
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Please install Python 3.9 or later first.
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating local virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create .venv.
        pause
        exit /b 1
    )
)

echo Installing or checking dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Starting local web console...
echo Open http://127.0.0.1:8765/ if the browser does not open automatically.
echo Keep this window open while using JNUAutoElective.
echo.
".venv\Scripts\python.exe" -m jnu_auto_elective web

pause
