@echo off
setlocal

set REPO_URL=https://github.com/enrmonloz/proyectoAmazon.git
set PROJECT_DIR=proyectoAmazon
set BRANCH=scenarios

echo =====================================
echo Instalador del proyecto Amazon Sevilla
echo =====================================

where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: Git no esta instalado.
    echo Instala Git desde https://git-scm.com/download/win
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en PATH.
    echo Instala Python 3.11 o superior y marca "Add Python to PATH".
    pause
    exit /b 1
)

if exist "%PROJECT_DIR%" (
    echo El repositorio ya existe. Actualizando...
    cd "%PROJECT_DIR%"
    git fetch
    git checkout %BRANCH%
    git pull
) else (
    echo Clonando repositorio...
    git clone -b %BRANCH% %REPO_URL% "%PROJECT_DIR%"
    cd "%PROJECT_DIR%"
)

echo Creando entorno virtual...
python -m venv .venv

echo Activando entorno...
call .venv\Scripts\activate.bat

echo Actualizando pip...
python -m pip install --upgrade pip

echo Instalando dependencias...
pip install -r requirements.txt

echo.
echo Instalacion completada.
echo Para ejecutar la app, entra en la carpeta %PROJECT_DIR% y haz doble clic en run.bat
echo.
pause