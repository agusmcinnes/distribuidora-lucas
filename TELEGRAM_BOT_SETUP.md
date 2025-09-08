# 🤖 Configuración del Bot de Telegram

## Resumen

Esta guía te ayudará a configurar el bot de Telegram para recibir alertas automáticas cuando lleguen nuevos emails al sistema.

## 📋 Requisitos Previos

1. **Cuenta de Telegram** activa
2. **Redis** instalado (para Celery)
3. **Dependencias instaladas** (`pip install -r requirements.txt`)

## 🚀 Configuración Paso a Paso

### 1. Crear el Bot en Telegram

1. **Abre Telegram** y busca `@BotFather`
2. **Inicia conversación** con `/start`
3. **Crea un nuevo bot** con `/newbot`
4. **Elige un nombre** para tu bot (ej: "Distribuidora Lucas Alerts")
5. **Elige un username** único (debe terminar en "bot", ej: "distribuidora_lucas_bot")
6. **Guarda el token** que te proporciona (será algo como: `123456789:ABCDEF...`)

### 2. Obtener tu Chat ID

1. **Envía un mensaje** a tu bot recién creado
2. **Ve a esta URL** en tu navegador:
   ```
   https://api.telegram.org/bot<TU_TOKEN>/getUpdates
   ```
   Reemplaza `<TU_TOKEN>` con el token que obtuviste de BotFather
3. **Busca en la respuesta** algo como:
   ```json
   "chat": {
     "id": 123456789,
     "first_name": "Tu Nombre",
     "type": "private"
   }
   ```
4. **Guarda el número** del `"id"` (ese es tu Chat ID)

### 3. Configuración Automática (Recomendado)

Ejecuta el script de configuración automática:

```bash
setup_telegram_bot.bat
```

Este script te pedirá:

- **Token del bot** (el que obtuviste de BotFather)
- **Chat ID** (el que obtuviste en el paso anterior)

El script hará toda la configuración automáticamente y enviará un mensaje de prueba.

### 4. Configuración Manual

Si prefieres configurar manualmente:

#### 4.1 Editar el archivo .env

```bash
# Configuración Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCDEF1234567890abcdef1234567890ABC
TELEGRAM_DEFAULT_CHAT_ID=123456789
```

#### 4.2 Ejecutar migraciones

```bash
cd app
python manage.py makemigrations telegram_bot
python manage.py migrate
```

#### 4.3 Configurar el bot

```bash
python manage.py setup_telegram --token "TU_TOKEN" --chat-id TU_CHAT_ID
```

## 🧪 Probar la Configuración

### Probar conexión básica:

```bash
cd app
python manage.py test_telegram_bot --info
```

### Probar envío de mensaje:

```bash
python manage.py test_telegram_bot --chat-id TU_CHAT_ID
```

### Probar todos los chats configurados:

```bash
python manage.py test_telegram_bot --test-all
```

## 🔄 Configurar Webhook (Producción)

Para usar webhooks en lugar de polling (recomendado para producción):

### 1. Configurar URL del webhook

```bash
python manage.py setup_telegram_webhook --url "https://tudominio.com/telegram/webhook/"
```

### 2. Con token secreto (recomendado):

```bash
python manage.py setup_telegram_webhook --url "https://tudominio.com/telegram/webhook/" --secret "mi-token-secreto"
```

### 3. Ver información del webhook:

```bash
python manage.py setup_telegram_webhook --info
```

### 4. Eliminar webhook:

```bash
python manage.py setup_telegram_webhook --delete
```

## ⚙️ Administración desde Django Admin

1. **Ve a** `http://localhost:8000/admin`
2. **En la sección "Telegram Bot"** encontrarás:

### Configuraciones de Telegram

- Gestionar tokens de bots
- Configurar webhooks
- Activar/desactivar bots

### Chats de Telegram

- Agregar nuevos chats para alertas
- Configurar nivel de alertas por chat (Alta, Media, Baja, Todas)
- Activar/desactivar alertas de email o sistema
- Gestionar diferentes tipos de chat (privado, grupo, canal)

### Mensajes de Telegram

- Ver historial de mensajes enviados
- Reintentar mensajes fallidos
- Monitorear estado de envíos

## 🔧 Configuración Avanzada

### Niveles de Alertas

Puedes configurar qué chats reciben qué tipo de alertas:

- **Alta**: Solo emails de alta prioridad
- **Media**: Emails de alta y media prioridad
- **Baja**: Emails de baja prioridad
- **Todas**: Todos los emails

### Palabras Clave de Prioridad

Configura en el `.env`:

```bash
# Alta prioridad
HIGH_PRIORITY_KEYWORDS=venta,urgente,importante,alerta,crítico,error,factura,pago

# Media prioridad
MEDIUM_PRIORITY_KEYWORDS=pedido,orden,consulta,información,cotización,producto

# Baja prioridad
LOW_PRIORITY_KEYWORDS=newsletter,promoción,marketing,notificación,boletín
```

### Múltiples Chats

Puedes configurar múltiples chats desde el admin:

1. **Chat del gerente**: Solo alertas de alta prioridad
2. **Chat del equipo**: Alertas de alta y media prioridad
3. **Canal de notificaciones**: Todas las alertas

## 🚨 Solución de Problemas

### Error: "Bot no encontrado"

- Verifica que el token sea correcto
- Asegúrate de que el bot no haya sido eliminado

### Error: "Chat no encontrado"

- Verifica que el Chat ID sea correcto
- Asegúrate de haber enviado un mensaje al bot primero

### Error: "Forbidden"

- El bot fue bloqueado por el usuario
- Debes desbloquear el bot en Telegram

### No llegan las alertas

1. Verifica que Celery esté ejecutándose:
   ```bash
   start_celery_worker.bat
   start_celery_beat.bat
   ```
2. Revisa los logs:
   ```bash
   type app\logs\imap_handler.log
   ```
3. Verifica que el chat esté marcado como activo en el admin

## 📱 Comandos del Bot

Tu bot responderá a estos comandos:

- `/start`: Información del bot
- `/help`: Ayuda y comandos disponibles
- `/status`: Estado del bot y información del chat

## 🔐 Seguridad

### Para Webhooks:

- Usa HTTPS siempre
- Configura un token secreto
- Valida la fuente de los requests

### Para el Bot:

- No compartas el token públicamente
- Regenera el token si se compromete
- Limita los chats que pueden interactuar

## 📊 Monitoreo

### Logs de Telegram:

```bash
# Ver logs en tiempo real
tail -f app/logs/imap_handler.log | grep -i telegram
```

### Estadísticas en Admin:

- Mensajes enviados por día
- Tasa de éxito de envíos
- Chats más activos

---

✅ **¡Listo!** Tu bot de Telegram está configurado y enviará alertas automáticamente cuando lleguen nuevos emails.
