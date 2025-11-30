@echo off
title Servidor Totem Check-in
setlocal enabledelayedexpansion

echo ==================================
echo   INICIANDO SERVIDOR DJANGO
echo ==================================

rem Diretório do projeto (onde o .bat está)
set "PROJ_DIR=%~dp0"
cd /d "%PROJ_DIR%"

rem Nome do ambiente Conda
set "ENV_NAME=TotemCheckin"

rem Caminho para salvar configuração local
set "CONFIG_FILE=%PROJ_DIR%\.env_config"

rem Verifica se já existe um caminho salvo do Miniconda
if exist "%CONFIG_FILE%" (
    for /f "usebackq tokens=*" %%A in ("%CONFIG_FILE%") do set "CONDA_DIR=%%A"
    if exist "!CONDA_DIR!\Scripts\activate.bat" (
        echo [INFO] Usando caminho salvo do Miniconda: !CONDA_DIR!
        goto :FOUND_CONDA
    ) else (
        echo [AVISO] Caminho salvo nao encontrado. Vou procurar novamente...
    )
)

rem Tenta localizar automaticamente o Miniconda em locais comuns
for %%D in ("%USERPROFILE%\miniconda3" "C:\ProgramData\miniconda3" "D:\miniconda3") do (
    if exist "%%~D\Scripts\activate.bat" (
        set "CONDA_DIR=%%~D"
        echo [INFO] Miniconda encontrado automaticamente em: %%~D
        echo %%~D>"%CONFIG_FILE%"
        goto :FOUND_CONDA
    )
)

rem Se nao encontrou, pede para o usuário informar manualmente
echo [ERRO] Nao foi possivel localizar o Miniconda automaticamente.
set /p CONDA_DIR=Digite o caminho completo do Miniconda (ex: C:\Users\SeuUsuario\miniconda3): 
if not exist "%CONDA_DIR%\Scripts\activate.bat" (
    echo [ERRO] Caminho invalido. Fechando...
    timeout /t 5 >nul
    exit /b
)
echo %CONDA_DIR%>"%CONFIG_FILE%"
echo [INFO] Caminho salvo para uso futuro.

:FOUND_CONDA
echo.
echo [INFO] Ativando ambiente Conda: %ENV_NAME%
call "%CONDA_DIR%\Scripts\activate.bat" %ENV_NAME%

rem Detecta o IPv4 local automaticamente
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /R /C:"IPv4"') do (
    set ip=%%a
    set ip=!ip: =!
)

echo.
echo [INFO] Endereco externo(acesse na mesma rede): https://!ip!:8000
echo [INFO] Endereco localhost:       https://localhost:8000
echo ----------------------------------

rem Abre o navegador no endereço local
start "" https://localhost:8000

echo [INFO] Iniciando servidor Django...
python manage.py runserver_plus --cert-file cert.pem --key-file key.pem 0.0.0.0:8000

echo.
echo ==================================
echo   SERVIDOR ENCERRADO
echo ==================================

timeout /t 2 >nul
exit
