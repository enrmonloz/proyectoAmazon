@echo off
setlocal

echo Iniciando app Amazon Sevilla...

if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: No existe el entorno virtual.
    echo Ejecuta primero setup.bat
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

streamlit run app.py

pause