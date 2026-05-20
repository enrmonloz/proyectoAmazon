@echo off
setlocal

echo Actualizando proyecto...

git pull

call .venv\Scripts\activate.bat

pip install -r requirements.txt

echo.
echo Proyecto actualizado.
echo.
pause