@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Visualizacao Meteorologica OpenGL

if not exist ".venv\Scripts\python.exe" (
    echo As bibliotecas ainda nao foram instaladas.
    echo Execute instalar_windows.bat primeiro.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
python main.py
if errorlevel 1 pause

