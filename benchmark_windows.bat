@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Benchmark - Meteorologia OpenGL

if not exist ".venv\Scripts\python.exe" (
    echo Execute instalar_windows.bat primeiro.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
python main.py --benchmark --seconds 12 --no-vsync
echo.
echo Os resultados foram salvos na pasta outputs.
pause

