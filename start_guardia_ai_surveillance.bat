@echo off
echo 🚀 Starting Guardia AI Enhanced Surveillance System
echo ========================================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.7+ and try again
    pause
    exit /b 1
)

echo ✅ Python found

REM Check if required directories exist
if not exist "src" (
    echo ❌ Source directory not found
    echo Please ensure you're running this from the project root
    pause
    exit /b 1
)

if not exist "logs" mkdir logs
if not exist "recordings" mkdir recordings
if not exist "images" mkdir images
if not exist "encodings" mkdir encodings

echo ✅ Directories ready

REM Install dependencies if needed
echo 🔧 Checking dependencies...
python -c "import cv2, numpy, face_recognition" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️ Installing missing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ Failed to install dependencies
        echo Please run: pip install -r requirements.txt
        pause
        exit /b 1
    )
)

echo ✅ Dependencies ready

REM Start the enhanced surveillance system
echo 🎥 Starting Enhanced Surveillance System...
echo ========================================================
echo.
echo 🎯 Choose your surveillance mode:
echo   1. Main Application Menu (Login required)
echo   2. Enhanced Demo (No login required)
echo   3. System Verification
echo.
set /p choice="Select option (1-3): "

if "%choice%"=="1" (
    echo Starting main application...
    cd src
    python main.py
) else if "%choice%"=="2" (
    echo Starting enhanced demo...
    python demo_enhanced_surveillance.py
) else if "%choice%"=="3" (
    echo Running system verification...
    python verify_enhanced_surveillance.py
) else (
    echo ❌ Invalid choice. Starting main application...
    cd src
    python main.py
)

echo.
echo 👋 Guardia AI Enhanced Surveillance System stopped
pause
