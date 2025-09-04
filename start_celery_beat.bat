@echo off
title Procesamiento Email - Distribuidora Lucas
color 0C

echo ============================================
echo    INICIANDO PROCESAMIENTO DE EMAILS
echo ============================================
echo.

echo Activando entorno virtual...
call .envs\lucas\Scripts\activate.bat

echo.
echo Iniciando monitoreo de emails cada 5 minutos...
echo MANTÉN ESTA VENTANA ABIERTA
echo.

cd app
C:\Users\Usuario\OneDrive\Escritorio\Proyectos\distribuidora-lucas\.envs\lucas\Scripts\celery.exe -A app beat --loglevel=info

pause
