@echo off
title Celery Worker - Alertas Email
color 0B

echo ============================================
echo    INICIANDO SISTEMA DE ALERTAS
echo ============================================
echo.

echo Activando entorno virtual...
call .envs\lucas\Scripts\activate.bat

echo.
echo Iniciando procesamiento de alertas...
echo MANTÉN ESTA VENTANA ABIERTA
echo.

cd app
C:\Users\Usuario\OneDrive\Escritorio\Proyectos\distribuidora-lucas\.envs\lucas\Scripts\celery.exe -A app worker --loglevel=info --pool=solo

pause
