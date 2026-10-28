@echo off
setlocal
python -m pip install -r requirements.txt
pyinstaller --noconfirm --clean --windowed --hidden-import babel.numbers --add-data "app\assets;app\assets" --name FarmaStock main.py
if errorlevel 1 (
  echo Error al generar el ejecutable.
  pause
  exit /b 1
)
echo.
echo Ejecutable generado en dist\FarmaStock\
pause
