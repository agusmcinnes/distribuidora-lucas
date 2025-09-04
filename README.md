# 🚚 Sistema de Alertas - Distribuidora Lucas

## 📄 Descripción

Sistema automatizado para procesar emails IMAP y enviar alertas por Telegram cuando lleguen nuevos emails. Diseñado específicamente para Distribuidora Lucas para mantener al equipo informado sobre nuevos pedidos, consultas y comunicaciones importantes.

## ✨ Características

- 📧 **Procesamiento automático de emails** via IMAP
- 🤖 **Alertas por Telegram** en tiempo real
- ⚡ **Procesamiento asíncrono** con Celery
- 🎯 **Clasificación automática por prioridad** basada en palabras clave
- 👥 **Múltiples chats** con diferentes niveles de alerta
- 📊 **Panel de administración** Django completo
- 🔄 **Webhook de Telegram** para producción
- 📱 **Bot interactivo** con comandos básicos

## 🚀 Inicio Rápido

### 1. Configuración Inicial

```bash
# Clonar el repositorio
git clone <repository-url>
cd distribuidora-lucas

# Ejecutar configuración automática
setup_telegram_bot.bat
```

### 2. Configurar Variables de Entorno

Copia `.env.example` a `.env` y completa:

```bash
# Email
IMAP_EMAIL=tu-email@gmail.com
IMAP_PASSWORD=tu-app-password

# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCDEF...
TELEGRAM_DEFAULT_CHAT_ID=123456789
```

### 3. Iniciar Sistema Completo

```bash
start_complete_system.bat
```

## 📋 Requisitos

- Python 3.8+
- Redis Server
- Cuenta de Gmail con App Password
- Bot de Telegram (creado con @BotFather)

## 📦 Instalación Detallada

### 1. Clonar y Configurar Entorno

```bash
git clone <repository-url>
cd distribuidora-lucas
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar Base de Datos

```bash
cd app
python manage.py migrate
python manage.py createsuperuser
```

### 3. Configurar Telegram

Ver guía completa en: [TELEGRAM_BOT_SETUP.md](TELEGRAM_BOT_SETUP.md)

## 🔧 Uso

### Comandos Principales

```bash
# Configurar bot de Telegram
python manage.py setup_telegram --token "TU_TOKEN" --chat-id TU_CHAT_ID

# Probar conexión
python manage.py test_telegram_bot --test-all

# Procesar emails manualmente
python manage.py process_imap_emails

# Configurar webhook (producción)
python manage.py setup_telegram_webhook --url "https://tudominio.com/telegram/webhook/"
```

### Scripts de Windows

```bash
# Configuración automática de Telegram
setup_telegram_bot.bat

# Iniciar sistema completo
start_complete_system.bat

# Servicios individuales
start_celery_worker.bat
start_celery_beat.bat
```

## 📊 Panel de Administración

Accede a `http://localhost:8000/admin` para:

- 🤖 Gestionar configuraciones de Telegram
- 💬 Configurar chats y niveles de alerta
- 📧 Ver historial de emails procesados
- 📱 Monitorear mensajes de Telegram enviados
- ⚙️ Configurar cuentas IMAP

## 🎯 Clasificación de Prioridades

El sistema clasifica automáticamente los emails:

### 🚨 Alta Prioridad

- venta, urgente, importante, alerta, crítico, error, factura, pago

### 📧 Media Prioridad

- pedido, orden, consulta, información, cotización, producto

### 📩 Baja Prioridad

- newsletter, promoción, marketing, notificación, boletín

## 🔄 Arquitectura

```
📧 Gmail IMAP → 🔄 Celery Tasks → 📊 Django Admin
                       ↓
🤖 Telegram Bot ← 📱 Webhooks ← 💾 SQLite DB
```

### Componentes:

- **Django**: Framework web y panel de administración
- **Celery**: Procesamiento asíncrono de tareas
- **Redis**: Broker para Celery
- **SQLite**: Base de datos local
- **Telegram Bot API**: Envío de alertas
- **IMAP**: Conexión con Gmail

## 📁 Estructura del Proyecto

```
distribuidora-lucas/
├── app/
│   ├── app/                 # Configuración Django
│   ├── company/             # Gestión de empresas
│   ├── emails/              # Modelo de emails
│   ├── imap_handler/        # Procesamiento IMAP
│   ├── telegram_bot/        # Bot de Telegram (NUEVO)
│   ├── user/                # Gestión de usuarios
│   └── logs/                # Archivos de log
├── scripts/                 # Scripts de configuración
├── TELEGRAM_BOT_SETUP.md   # Guía de Telegram
└── requirements.txt         # Dependencias
```

## 🤖 Bot de Telegram

### Comandos Disponibles:

- `/start` - Información del bot
- `/help` - Ayuda y comandos
- `/status` - Estado del bot

### Configuración de Chats:

- **Privados**: Para usuarios individuales
- **Grupos**: Para equipos
- **Canales**: Para notificaciones masivas

### Niveles de Alerta:

- **Alta**: Solo emails críticos
- **Media**: Emails importantes
- **Baja**: Solo newsletters
- **Todas**: Todos los emails

## 🔐 Seguridad

- 🔑 App Passwords para Gmail
- 🛡️ Tokens secretos para webhooks
- 🔒 Validación de orígenes
- 📝 Logs de auditoría completos

## 🚨 Solución de Problemas

### Email no se procesa:

1. Verificar credenciales IMAP
2. Revisar logs: `type app\logs\imap_handler.log`
3. Verificar conexión a internet

### Telegram no envía:

1. Verificar token del bot
2. Verificar Chat ID
3. Probar: `python manage.py test_telegram_bot --test-all`

### Celery no funciona:

1. Verificar Redis está ejecutándose
2. Reiniciar worker: `start_celery_worker.bat`
3. Revisar logs de Celery

## 📈 Monitoreo

### Logs Principales:

```bash
# Logs del sistema IMAP
type app\logs\imap_handler.log

# Logs de Django
type app\logs\django.log

# Ver en tiempo real
tail -f app/logs/imap_handler.log
```

### Métricas en Admin:

- Emails procesados por día
- Alertas de Telegram enviadas
- Tasa de éxito de notificaciones
- Chats más activos

## 🛠️ Desarrollo

### Ejecutar Tests:

```bash
cd app
python manage.py test
```

### Configurar Desarrollo:

```bash
# Modo debug
DEBUG=True

# Webhook local con ngrok
ngrok http 8000
python manage.py setup_telegram_webhook --url "https://abc123.ngrok.io/telegram/webhook/"
```

## 📞 Soporte

Para problemas o mejoras:

1. 📋 Revisar logs del sistema
2. 🧪 Ejecutar tests de conexión
3. 📖 Consultar documentación
4. 🔧 Usar comandos de diagnóstico

## 📄 Licencia

Proyecto privado para Distribuidora Lucas.

---

🚚 **Distribuidora Lucas** - Sistema de Alertas Automatizado
