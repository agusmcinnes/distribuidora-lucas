@echo off
title Sistema de Alertas - Distribuidora Lucas
color 0E

echo ============================================
echo    SISTEMA DE ALERTAS EMAIL → TELEGRAM
echo ============================================
echo.
echo ✅ Bot configurado: @LucasDisBot
echo ✅ Chat ID: 6514522814
echo.
echo Este sistema:
echo 1. Monitorea emails cada 5 minutos
echo 2. Envia alertas automáticas a Telegram
echo.
echo ============================================
echo    INICIANDO SERVICIOS
echo ============================================
echo.
echo IMPORTANTE: Se abrirán 2 ventanas adicionales
echo - Una para procesar alertas (Worker)
echo - Una para monitorear emails (Beat)
echo.
echo MANTÉN TODAS LAS VENTANAS ABIERTAS
echo.
pause

echo Iniciando procesador de alertas...
start "Alertas Telegram" cmd /k "start_celery_worker.bat"

timeout /t 2

echo Iniciando monitor de emails...
start "Monitor Emails" cmd /k "start_celery_beat.bat"

echo.
echo ============================================
echo    ✅ SISTEMA INICIADO CORRECTAMENTE
echo ============================================
echo.
echo 📧 El sistema ahora monitorea emails automáticamente
echo 📱 Las alertas se envían por Telegram al instante
echo.
echo Para detener: Cierra todas las ventanas
echo Para admin: http://localhost:8000/admin
echo.
pause
