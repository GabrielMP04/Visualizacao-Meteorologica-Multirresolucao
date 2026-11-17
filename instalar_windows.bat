@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Instalacao - Projeto Meteorologia OpenGL

echo ==========================================================
echo  INSTALADOR - VISUALIZACAO METEOROLOGICA OPENGL
echo ==========================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python nao encontrado.
    echo Instale o Python 3.11 ou 3.12 em https://www.python.org/downloads/
    echo Durante a instalacao, marque a opcao "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    py -3.12 -m venv .venv 2>nul
    if errorlevel 1 py -3 -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
    echo Nao foi possivel criar o ambiente virtual.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
echo Atualizando o instalador de pacotes...
python -m pip install --upgrade pip
if errorlevel 1 goto :erro

echo Instalando bibliotecas obrigatorias...
python -m pip install -r requirements.txt
if errorlevel 1 goto :erro

echo Tentando instalar a aceleracao opcional do PyOpenGL...
python -m pip install PyOpenGL_accelerate
if errorlevel 1 echo A aceleracao opcional nao foi instalada. O projeto funcionara normalmente.

echo.
echo Instalacao concluida com sucesso.
echo Execute executar_windows.bat para abrir o projeto.
pause
exit /b 0

:erro
echo.
echo Ocorreu um erro durante a instalacao.
echo Verifique sua conexao e tente novamente.
pause
exit /b 1

