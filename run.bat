@echo off
echo 🛡️ Guardia AI - Smart Home Surveillance System
echo ===============================================

if "%1"=="" (
    echo Usage: run.bat [setup^|run^|docker^|docker-minimal^|status^|clean^|help]
    echo.
    echo Commands:
    echo   setup         - Setup the project environment
    echo   run           - Run the application natively
    echo   docker        - Run using Docker (full version)
    echo   docker-minimal- Run using Docker (minimal version)
    echo   status        - Show current status
    echo   clean         - Clean all data
    echo   help          - Show help
    echo.
    echo Example: run.bat setup
    pause
    exit /b
)

if "%1"=="docker-minimal" (
    echo 🐳 Starting minimal Docker version...
    docker-compose --profile minimal up --build guardia-ai-minimal
    goto :end
)

python runner.py %1

:end
if errorlevel 1 (
    echo.
    echo ❌ Command failed. Check the output above.
    echo.
    echo 🔧 Troubleshooting options:
    echo 1. Try: run.bat docker-minimal
    echo 2. Try: run.bat run (native mode)
    echo 3. Check Docker Desktop is running
    pause
)
