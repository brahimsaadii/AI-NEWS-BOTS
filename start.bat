@echo off
echo News Tweet Bots - Starting System
echo ================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo WARNING: .env file not found
    echo Please copy .env.example to .env and configure your API keys
    echo.
    echo Do you want to continue anyway? (y/n)
    set /p continue=
    if /i not "%continue%"=="y" (
        echo Setup cancelled
        pause
        exit /b 1
    )
)

echo Starting BotFather...
echo.
python main.py

pause
