@echo off
echo ==================================
echo Employee Attendance System Setup
echo ==================================
echo.

:: Check Python installation
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed!
    echo Please install Python 3.8 or higher from https://www.python.org/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo √ Python %PYTHON_VERSION% found
echo.

:: Install dependencies
echo Installing required packages...
pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo √ All packages installed successfully
echo.

:: Create directories
echo Setting up directories...
if not exist "uploads\" mkdir uploads
echo √ Directories created
echo.

echo ==================================
echo Setup Complete!
echo ==================================
echo.
echo To start the application, run:
echo   python app.py
echo.
echo Then open your browser and go to:
echo   http://localhost:5000
echo.
echo Sample attendance file included:
echo   sample_attendance.xlsx
echo.
echo ==================================
pause
