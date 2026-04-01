@echo off
REM Quantum 3D Visualization Launcher for Windows

echo ========================================
echo Mind Link - Quantum 3D Visualization
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

echo Checking dependencies...
python -c "import pygame" 2>nul
if errorlevel 1 (
    echo.
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo Starting visualization...
echo.
echo Controls:
echo   SPACE - Next stage
echo   R - Reset
echo   C - Toggle camera rotation
echo   1-4 - Switch motor imagery patterns
echo   ESC - Quit
echo.

python quantum_3d_viz.py

if errorlevel 1 (
    echo.
    echo ERROR: Visualization failed to start
    pause
)
