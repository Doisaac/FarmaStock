
@echo off
setlocal

REM Ir a la carpeta del proyecto
cd /d "%~dp0"

echo ========================================
echo    FARMASTOCK 1.0.0 - COMPILACION
echo ========================================
echo.

REM Utilizar el entorno virtual si existe
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

REM Instalar dependencias
echo [1/3] Verificando dependencias...
"%PYTHON%" -m pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: No se pudieron instalar las dependencias.
    pause
    exit /b 1
)

REM Compilar utilizando la configuracion oficial
echo.
echo [2/3] Compilando FarmaStock...
"%PYTHON%" -m PyInstaller --noconfirm --clean FarmaStock.spec

if errorlevel 1 (
    echo ERROR: No se pudo generar el ejecutable.
    pause
    exit /b 1
)

REM Comprobar los archivos generados
echo.
echo [3/3] Verificando ejecutable...

if not exist "dist\FarmaStock\FarmaStock.exe" (
    echo ERROR: No se encontro FarmaStock.exe.
    pause
    exit /b 1
)

if not exist "dist\FarmaStock\_internal" (
    echo ERROR: No se encontro la carpeta de dependencias.
    pause
    exit /b 1
)

echo.
echo ========================================
echo    COMPILACION FINALIZADA
echo ========================================
echo.
echo Ejecutable:
echo dist\FarmaStock\FarmaStock.exe
echo.
echo El sistema esta listo para probarse.
echo.

pause
exit /b 0
