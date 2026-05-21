@echo off
setlocal EnableExtensions

set "REPO_URL=https://github.com/enrmonloz/vrp_tiempo_svq1.git"
set "PROJECT_DIR=proyectoAmazon"
set "BRANCH=reestructuracion-codigo"
set "GIT_WINGET_ID=Git.Git"
set "PYTHON_WINGET_ID=Python.Python.3.11"
set "PYTHON_CMD="
set "TARGET_DIR="

echo =====================================
echo Instalador del proyecto Amazon Sevilla
echo =====================================
echo.

pushd "%~dp0" >nul 2>nul
if errorlevel 1 (
    echo ERROR: No se pudo entrar en la carpeta del instalador.
    goto fail
)

call :ensure_git || goto fail
call :ensure_python || goto fail
call :prepare_project || goto fail
call :prepare_virtualenv || goto fail

echo.
echo =====================================
echo Instalacion completada
echo =====================================
echo Proyecto listo en:
echo   %TARGET_DIR%
echo.
echo Para ejecutar la app, haz doble clic en:
echo   %TARGET_DIR%\run.bat
echo.
echo O ejecuta estos comandos:
echo   cd /d "%TARGET_DIR%"
echo   run.bat
echo.
popd >nul 2>nul
pause
exit /b 0

:fail
echo.
echo =====================================
echo Instalacion interrumpida
echo =====================================
echo Revisa el mensaje anterior y vuelve a ejecutar setup.bat.
echo.
popd >nul 2>nul
pause
exit /b 1

:ensure_winget
where winget >nul 2>nul
if not errorlevel 1 exit /b 0

echo ERROR: winget no esta disponible en este Windows.
echo Instala "App Installer" desde Microsoft Store o instala manualmente:
echo   - Git: https://git-scm.com/download/win
echo   - Python 3.11: https://www.python.org/downloads/windows/
echo Despues vuelve a ejecutar setup.bat.
exit /b 1

:detect_git
where git >nul 2>nul
if not errorlevel 1 exit /b 0

if exist "%ProgramFiles%\Git\cmd\git.exe" (
    set "PATH=%ProgramFiles%\Git\cmd;%PATH%"
    exit /b 0
)

if exist "%LocalAppData%\Programs\Git\cmd\git.exe" (
    set "PATH=%LocalAppData%\Programs\Git\cmd;%PATH%"
    exit /b 0
)

exit /b 1

:ensure_git
call :detect_git
if not errorlevel 1 (
    echo Git detectado.
    exit /b 0
)

echo Git no esta instalado. Intentando instalarlo con winget...
call :ensure_winget || exit /b 1
winget install --id "%GIT_WINGET_ID%" -e --source winget --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo ERROR: winget no pudo instalar Git.
    echo Instala Git manualmente desde https://git-scm.com/download/win y vuelve a ejecutar setup.bat.
    exit /b 1
)

call :detect_git
if errorlevel 1 (
    echo Git parece haberse instalado, pero esta ventana todavia no lo detecta.
    echo Cierra esta ventana y vuelve a ejecutar setup.bat.
    exit /b 1
)

echo Git instalado y detectado.
exit /b 0

:detect_python
py -3.11 --version >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.11"
    exit /b 0
)

py -3 --version >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    exit /b 0
)

python --version >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    exit /b 0
)

if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    set "PYTHON_CMD="%LocalAppData%\Programs\Python\Python311\python.exe""
    exit /b 0
)

if exist "%ProgramFiles%\Python311\python.exe" (
    set "PYTHON_CMD="%ProgramFiles%\Python311\python.exe""
    exit /b 0
)

exit /b 1

:ensure_python
call :detect_python
if not errorlevel 1 (
    echo Python detectado: %PYTHON_CMD%
    exit /b 0
)

echo Python 3 no esta instalado o no esta en PATH. Intentando instalar Python 3.11 con winget...
call :ensure_winget || exit /b 1
winget install --id "%PYTHON_WINGET_ID%" -e --source winget --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo ERROR: winget no pudo instalar Python 3.11.
    echo Instala Python 3.11 manualmente desde https://www.python.org/downloads/windows/
    echo Marca la opcion "Add python.exe to PATH" y vuelve a ejecutar setup.bat.
    exit /b 1
)

call :detect_python
if errorlevel 1 (
    echo Python parece haberse instalado, pero esta ventana todavia no lo detecta.
    echo Cierra esta ventana y vuelve a ejecutar setup.bat.
    exit /b 1
)

echo Python instalado y detectado: %PYTHON_CMD%
exit /b 0

:prepare_project
if exist "app.py" if exist "requirements.txt" goto local_project
if exist "%PROJECT_DIR%" goto existing_project_dir
goto clone_project

:local_project
set "TARGET_DIR=%CD%"
echo Proyecto detectado en la carpeta actual.
if exist ".git" (
    echo Se respetara esta copia local sin cambiar de rama desde el propio instalador.
)
exit /b 0

:existing_project_dir
if not exist "%PROJECT_DIR%\app.py" goto invalid_project_dir
if not exist "%PROJECT_DIR%\requirements.txt" goto invalid_project_dir

pushd "%PROJECT_DIR%" >nul 2>nul
if errorlevel 1 (
    echo ERROR: No se pudo entrar en "%PROJECT_DIR%".
    exit /b 1
)

set "TARGET_DIR=%CD%"
echo Proyecto detectado en "%TARGET_DIR%".
call :update_project_if_git
set "PROJECT_RESULT=%ERRORLEVEL%"
popd >nul 2>nul
exit /b %PROJECT_RESULT%

:invalid_project_dir
echo ERROR: Existe una carpeta "%PROJECT_DIR%", pero no parece contener este proyecto.
echo Renombrala o eliminala y vuelve a ejecutar setup.bat.
exit /b 1

:clone_project
echo Clonando repositorio...
echo   %REPO_URL%
echo Rama:
echo   %BRANCH%
git clone -b "%BRANCH%" "%REPO_URL%" "%PROJECT_DIR%"
if errorlevel 1 (
    echo ERROR: No se pudo clonar el repositorio.
    exit /b 1
)

pushd "%PROJECT_DIR%" >nul 2>nul
if errorlevel 1 (
    echo ERROR: No se pudo entrar en "%PROJECT_DIR%" despues de clonar.
    exit /b 1
)

set "TARGET_DIR=%CD%"
popd >nul 2>nul
exit /b 0

:update_project_if_git
if not exist ".git" (
    echo Proyecto sin carpeta .git. Se preparara sin intentar actualizar desde GitHub.
    exit /b 0
)

echo Actualizando repositorio...
git fetch origin "+refs/heads/%BRANCH%:refs/remotes/origin/%BRANCH%"
if errorlevel 1 (
    echo ERROR: No se pudo descargar la rama "%BRANCH%" desde origin.
    exit /b 1
)

git rev-parse --verify "%BRANCH%" >nul 2>nul
if errorlevel 1 (
    git checkout -b "%BRANCH%" "origin/%BRANCH%"
) else (
    git checkout "%BRANCH%"
)
if errorlevel 1 (
    echo ERROR: No se pudo cambiar a la rama "%BRANCH%".
    echo Si tienes cambios locales, guardalos y vuelve a ejecutar setup.bat.
    exit /b 1
)

git pull --ff-only origin "%BRANCH%"
if errorlevel 1 (
    echo ERROR: No se pudo actualizar con fast-forward.
    echo Revisa si hay cambios locales o conflictos y vuelve a ejecutar setup.bat.
    exit /b 1
)

exit /b 0

:prepare_virtualenv
if not defined TARGET_DIR (
    echo ERROR: No se pudo resolver la carpeta del proyecto.
    exit /b 1
)

pushd "%TARGET_DIR%" >nul 2>nul
if errorlevel 1 (
    echo ERROR: No se pudo entrar en "%TARGET_DIR%".
    exit /b 1
)

if not exist "requirements.txt" (
    echo ERROR: No existe requirements.txt en "%TARGET_DIR%".
    popd >nul 2>nul
    exit /b 1
)

if not exist "run.bat" (
    echo ERROR: No existe run.bat en "%TARGET_DIR%".
    popd >nul 2>nul
    exit /b 1
)

if exist ".venv\Scripts\python.exe" (
    echo Entorno virtual existente detectado.
) else (
    echo Creando entorno virtual...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo ERROR: No se pudo crear el entorno virtual.
        popd >nul 2>nul
        exit /b 1
    )
)

echo Actualizando pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: No se pudo actualizar pip.
    popd >nul 2>nul
    exit /b 1
)

echo Instalando dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: No se pudieron instalar las dependencias.
    popd >nul 2>nul
    exit /b 1
)

echo Comprobando Streamlit...
".venv\Scripts\python.exe" -m streamlit --version >nul 2>nul
if errorlevel 1 (
    echo ERROR: Streamlit no quedo instalado correctamente.
    popd >nul 2>nul
    exit /b 1
)

popd >nul 2>nul
exit /b 0
