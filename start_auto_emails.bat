@echo off
REM ====================================================================
REM    DISTRIBUIDORA LUCAS - PROCESAMIENTO AUTOMÁTICO DE EMAILS
REM    Procesa emails automáticamente cada 5 minutos SIN Redis
REM ====================================================================

cd /d "%~dp0app"

title Distribuidora Lucas - Procesador Automático

echo.
echo =====================================================
echo    🚀 DISTRIBUIDORA LUCAS - PROCESADOR AUTOMÁTICO
echo =====================================================
echo.

REM Verificar que estamos en el directorio correcto
if not exist "manage.py" (
    echo ❌ Error: No se encuentra manage.py
    echo Asegúrate de que este archivo esté en la raíz del proyecto
    pause
    exit /b 1
)

REM Activar entorno virtual
echo 📦 Activando entorno virtual...
call "..\.envs\lucas\Scripts\activate.bat"

if %errorlevel% neq 0 (
    echo ❌ Error activando entorno virtual
    pause
    exit /b 1
)

echo ✅ Entorno virtual activado
echo.

REM Mostrar configuración actual
echo 🔧 Configuración actual:
python -c "
import os
import sys
import django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()
from django.conf import settings
from dotenv import load_dotenv
load_dotenv('../.env')
print(f'   📧 Email: {settings.IMAP_EMAIL}')
print(f'   🏠 Host: {settings.IMAP_HOST}:{settings.IMAP_PORT}')
print(f'   📦 Lote: {settings.IMAP_BATCH_SIZE} emails')
print(f'   ⏱️ Cada: {settings.IMAP_PROCESS_INTERVAL} segundos ({settings.IMAP_PROCESS_INTERVAL/60:.1f} minutos)')
"

echo.
echo 🔄 Iniciando procesamiento automático...
echo    - Se ejecutará cada 5 minutos
echo    - Presiona Ctrl+C para detener
echo.

REM Iniciar procesamiento automático
python manage.py auto_process

echo.
echo 🛑 Procesamiento automático detenido
pause
