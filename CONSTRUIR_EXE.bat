@echo off
chcp 65001 >nul
title Construir AlmacenObra.exe
cd /d "%~dp0"

echo ============================================================
echo  Genera AlmacenObra.exe (un solo archivo, no necesita Python
echo  en las PC donde se use). Este paso se hace UNA sola vez.
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo No se encontro Python en esta PC.
    echo Instale Python 3.11+ desde https://www.python.org/downloads/
    echo marcando "Add Python to PATH", y vuelva a ejecutar este archivo.
    pause
    exit /b 1
)

echo [1/3] Instalando herramientas...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto error

echo [2/3] Verificando el programa...
python -m unittest -q
if errorlevel 1 goto error

echo [3/3] Construyendo el ejecutable (puede tardar 2-5 minutos)...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name AlmacenObra ^
  --add-data "app/database/schema_v1.sql;app/database" ^
  main.py
if errorlevel 1 goto error

copy /y "dist\AlmacenObra.exe" "AlmacenObra.exe" >nul
echo.
echo ============================================================
echo  LISTO: AlmacenObra.exe quedo en esta carpeta.
echo  Copielo a cualquier PC con Windows y abralo con doble clic.
echo ============================================================
explorer /select,"%~dp0AlmacenObra.exe"
pause
exit /b 0

:error
echo.
echo Ocurrio un error. Tome captura de esta ventana y enviela.
pause
exit /b 1
