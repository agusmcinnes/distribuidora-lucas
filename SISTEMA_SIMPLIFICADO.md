# Sistema de Alertas de Telegram - Versión Simplificada

## 📋 Resumen del Sistema

El sistema ha sido **completamente simplificado** para cumplir únicamente con el objetivo principal:
**"recibir un mail, enviarlo como alerta en telegram"**

## 🔄 Flujo de Trabajo Simplificado

```
📧 Nuevo Email → 🔔 Signal Django → 🤖 Servicio Telegram → 📱 Alerta Enviada
```

### 1. **Recepción de Email**

- Cuando llega un nuevo email al sistema (modelo `ReceivedEmail`)
- Se guarda en la base de datos

### 2. **Detección Automática**

- Django signal `post_save` detecta el nuevo email automáticamente
- Archivo: `telegram_bot/signals.py`

### 3. **Envío de Alerta**

- Se activa `TelegramNotificationService.send_email_alert()`
- Envía alerta a todos los chats activos de Telegram
- Archivo: `telegram_bot/services.py`

## 🗂️ Archivos Simplificados

### ✅ Archivos Mantenidos (Esenciales)

- `telegram_bot/models.py` - Modelos básicos (TelegramConfig, TelegramChat, TelegramMessage)
- `telegram_bot/services.py` - Servicio simplificado para envío de alertas
- `telegram_bot/signals.py` - Signal para detección automática de emails
- `telegram_bot/tasks.py` - Tarea de Celery simplificada
- `telegram_bot/admin.py` - Administración simplificada
- `telegram_bot/views.py` - Vista básica de estado
- `telegram_bot/urls.py` - URL de estado

### ❌ Archivos Eliminados (Innecesarios)

- ~~`webhook` funcionalidad~~ - Eliminada completamente
- ~~Comandos complejos de Telegram~~ - No necesarios
- ~~Scripts de configuración automática~~ - Simplificados
- ~~Múltiples management commands~~ - Reducidos al mínimo

## ⚙️ Configuración Actual

### 🤖 Bot de Telegram

- **Nombre**: @LucasDisBot
- **Token**: Configurado en `TelegramConfig`
- **Chat ID**: 6514522814 (Chat activo)

### 📧 Detección de Prioridad

- **ALTA**: Emails con palabras clave: "urgente", "importante", "critico", "emergencia"
- **NORMAL**: Resto de emails

### 🎨 Formato de Mensaje

```
🚨 Nuevo Email - Prioridad ALTA

De: sender@example.com
Asunto: URGENTE: Problema crítico
Hora: 15:30:25 04/01/2025

Vista previa:
Este es el contenido del email...
```

## 🚀 Cómo Usar el Sistema

### 1. **Verificar Estado**

```bash
# Verificar que todo esté configurado
python manage.py shell
from telegram_bot.models import TelegramConfig, TelegramChat
TelegramConfig.objects.filter(is_active=True).exists()
TelegramChat.objects.filter(is_active=True).exists()
```

### 2. **Probar Alertas**

```bash
# Probar envío directo
python test_simplified_alert.py

# Probar señales automáticas
python test_signals.py
```

### 3. **Sistema en Producción**

- Los emails se procesan automáticamente
- Las alertas se envían inmediatamente
- Sin necesidad de configuración adicional

## 🔧 Mantenimiento

### Ver Logs

```bash
tail -f logs/imap_handler.log
```

### Estado del Bot

```
GET /telegram/status/
```

## ✨ Funcionalidades Simplificadas

### ✅ Lo que SÍ hace el sistema:

1. ✅ Detecta emails nuevos automáticamente
2. ✅ Clasifica prioridad (ALTA/NORMAL)
3. ✅ Envía alertas a Telegram inmediatamente
4. ✅ Formatea mensajes con información clave
5. ✅ Registra actividad en logs

### ❌ Lo que NO hace (eliminado):

1. ❌ No maneja webhooks de Telegram
2. ❌ No procesa comandos complejos
3. ❌ No tiene interfaz web compleja
4. ❌ No maneja múltiples configuraciones
5. ❌ No tiene features innecesarias

## 🎯 Objetivo Cumplido

**El sistema ahora hace EXACTAMENTE lo que pediste:**

> "lo único que debe hacer el flujo de trabajo es: recibir un mail, enviarlo como alerta en telegram"

**✅ COMPLETADO - Sistema simplificado y funcional**
