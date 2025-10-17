# Guía de Configuración del Bot de Telegram Multi-Tenant

## Resumen de cambios realizados

Se ha implementado una arquitectura centralizada para el bot de Telegram que permite:

✅ **Un solo bot administrado por el superadmin** (esquema público)
✅ **Cada empresa configura sus propios chats** (esquema tenant)
✅ **Proceso simple para obtener Chat IDs** (comando `/get_chat_id`)
✅ **Separación clara de responsabilidades** entre superadmin y admins de empresa

---

## 📁 Archivos modificados

### Modelos
- **`telegram_bot/models.py`**: Agregados campos `company` a `TelegramChat` y `TelegramMessage`

### Configuración
- **`app/settings.py`**: Movido `telegram_bot` a `SHARED_APPS`

### Admin
- **`telegram_bot/admin.py`**: Reescrito completamente con admins separados para superadmin y tenants

### Servicios
- **`telegram_bot/services.py`**: Actualizado para usar bot centralizado del esquema público

### Comandos
- **`telegram_bot/management/commands/run_telegram_bot.py`**: Nuevo comando para ejecutar el bot y responder a comandos

---

## 🚀 Pasos para implementar

### 1. Crear y aplicar migraciones

Primero, asegúrate de que Docker esté corriendo y la base de datos accesible:

```bash
# Crear las migraciones para los nuevos campos
python manage.py makemigrations telegram_bot

# Aplicar migraciones en esquema público
python manage.py migrate_schemas --schema=public

# Aplicar migraciones en todos los tenants existentes
python manage.py migrate_schemas
```

**Importante:** Si ya tienes datos en `TelegramChat` o `TelegramMessage`, la migración fallará porque el campo `company` es obligatorio. Necesitarás:

- Opción A: Eliminar los datos existentes
- Opción B: Modificar la migración para hacerla en dos pasos (primero nullable, luego asignar valores, luego non-nullable)

---

### 2. Configurar el bot en el esquema público

#### A. Acceder al admin del superadmin

```
http://localhost:8000/admin/
```

O si usas un dominio específico para el esquema público:

```
http://public.localhost:8000/admin/
```

#### B. Crear la configuración del bot

1. Ve a **"Configuraciones de Telegram"**
2. Haz clic en **"Agregar configuración de telegram"**
3. Completa:
   - **Nombre**: "Bot Principal" (o el nombre que prefieras)
   - **Bot Token**: El token que te dio @BotFather
   - **Activo**: ✅ Marcado
4. Guarda

#### C. Verificar que el bot funciona

En el admin, deberías ver:
- ✅ Estado del bot
- 🤖 Información del bot (username, ID, etc.)

Si no aparece la información, verifica que el token sea correcto.

---

### 3. Iniciar el bot para responder a comandos

El bot necesita estar corriendo para responder al comando `/get_chat_id`:

```bash
# Modo daemon (recomendado para producción)
python manage.py run_telegram_bot --daemon

# Modo single (para pruebas)
python manage.py run_telegram_bot
```

**Tip:** En producción, ejecuta esto con `supervisord`, `systemd` o similar para mantenerlo corriendo en background.

**Con Docker:**

```bash
docker-compose exec web python manage.py run_telegram_bot --daemon
```

Deberías ver:

```
✅ Bot configurado: Bot Principal
🤖 Iniciando bot en modo daemon...
🔄 Bot escuchando comandos...
💡 Los usuarios pueden enviar /get_chat_id en sus grupos para obtener el Chat ID
⏸️  Presiona Ctrl+C para detener el bot
```

---

### 4. Configurar chats para una empresa (tenant)

#### A. Obtener el Chat ID

1. **Crea un grupo en Telegram** (o usa uno existente)
2. **Agrega el bot al grupo** (busca @tu_bot en Telegram)
3. **En el grupo, envía:** `/get_chat_id`
4. **El bot responderá con:**

```
🆔 Información del Chat

📛 Nombre: Mi Grupo de Alertas
🔢 Chat ID: -1001234567890
📱 Tipo: Supergroup

✅ ¿Cómo usar este ID?
...
```

5. **Copia el Chat ID** (ej: `-1001234567890`)

#### B. Registrar el chat en el admin de la empresa

1. Accede al admin del tenant:
   ```
   http://empresa1.localhost:8000/admin/
   ```

2. Ve a **"Chats de Telegram"**

3. Verás una **guía visual completa** con instrucciones paso a paso

4. Haz clic en **"Agregar Chat de Telegram"**

5. Completa:
   - **Nombre**: "Grupo Alertas Ventas" (o el nombre que quieras)
   - **Chat ID**: `-1001234567890` (el que copiaste)
   - **Tipo de chat**: Supergrupo
   - **Nivel de alertas**: Todas (o el que prefieras)
   - **Alertas de email**: ✅ Marcado
   - **Alertas del sistema**: (opcional)
   - **Activo**: ✅ Marcado

6. Guarda

#### C. Probar el envío

En el admin, selecciona el chat que acabas de crear y usa la acción:
**"Enviar mensaje de prueba"**

Deberías recibir un mensaje de prueba en tu grupo de Telegram.

---

## 🧪 Probar el flujo completo

### Prueba de envío de alertas de emails

1. Asegúrate de que tienes:
   - ✅ Bot configurado en esquema público
   - ✅ Bot corriendo (`run_telegram_bot`)
   - ✅ Chat configurado para la empresa
   - ✅ Configuración IMAP activa

2. Procesa emails manualmente:

```bash
python manage.py process_imap_emails
```

3. Los emails deberían:
   - Guardarse en la base de datos
   - Enviarse automáticamente al chat de Telegram configurado

4. Verifica en el admin del tenant:
   - **"Emails Recibidos"** → Deberías ver los emails procesados
   - **"Mensajes de Telegram"** → Deberías ver los mensajes enviados

---

## 📊 Estructura final

### Esquema Público (Superadmin)

**Acceso:** `http://localhost:8000/admin/` o `http://public.localhost:8000/admin/`

**Puede administrar:**
- ✅ Empresas (Companies)
- ✅ Configuración del Bot de Telegram (TelegramConfig)
- ✅ Ver todos los chats de todas las empresas
- ✅ Ver todos los mensajes de todas las empresas

**No puede:**
- ❌ Configurar chats de empresas individuales (eso lo hace cada empresa)

### Esquema Tenant (Admin de Empresa)

**Acceso:** `http://empresa1.localhost:8000/admin/`

**Puede administrar:**
- ✅ Sus propios chats de Telegram
- ✅ Ver sus propios mensajes de Telegram
- ✅ Configuración IMAP de su empresa
- ✅ Emails recibidos de su empresa
- ✅ Usuarios de su empresa

**No puede:**
- ❌ Ver o modificar el bot (eso lo hace el superadmin)
- ❌ Ver chats de otras empresas

---

## 🔧 Comandos útiles

### Gestión del bot

```bash
# Iniciar bot en modo daemon
python manage.py run_telegram_bot --daemon

# Iniciar bot con intervalo personalizado
python manage.py run_telegram_bot --daemon --interval 5

# Probar bot una sola vez (no daemon)
python manage.py run_telegram_bot
```

### Procesamiento de emails

```bash
# Procesar emails de todas las empresas
python manage.py process_imap_emails

# Procesar emails en modo daemon
python manage.py process_imap_emails --daemon
```

### Migraciones

```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar solo en público
python manage.py migrate_schemas --schema=public

# Aplicar en todos los tenants
python manage.py migrate_schemas

# Aplicar en un tenant específico
python manage.py migrate_schemas --schema=empresa1
```

---

## 🐛 Troubleshooting

### El bot no responde a /get_chat_id

**Problema:** Enviaste `/get_chat_id` pero el bot no responde.

**Solución:**
1. Verifica que el comando `run_telegram_bot` esté corriendo
2. Verifica los logs para ver si hay errores
3. Asegúrate de que el bot tenga permisos para leer mensajes en el grupo
4. Prueba enviar `/start` primero

### La migración falla por el campo company

**Problema:** Error al ejecutar migraciones: "Field 'company' doesn't have a default value"

**Solución:**
1. Si no tienes datos importantes, elimina los registros existentes:
   ```python
   python manage.py shell
   >>> from telegram_bot.models import TelegramChat, TelegramMessage
   >>> TelegramChat.objects.all().delete()
   >>> TelegramMessage.objects.all().delete()
   ```
2. Luego ejecuta las migraciones de nuevo

### No veo "Configuraciones de Telegram" en el admin

**Problema:** El módulo no aparece en el admin del superadmin.

**Solución:**
1. Verifica que estés accediendo desde el esquema público
2. Verifica que `telegram_bot` esté en `SHARED_APPS` en settings.py
3. Reinicia el servidor

### Las notificaciones no llegan

**Problema:** Los emails se procesan pero no llegan a Telegram.

**Solución:**
1. Verifica que el chat esté activo y tenga "Alertas de email" habilitadas
2. Verifica que la empresa tenga al menos un chat configurado
3. Prueba con "Enviar mensaje de prueba" desde el admin
4. Revisa los logs del servidor

---

## 📝 Notas importantes

1. **Bot token:** Guarda el token del bot en un lugar seguro. Si lo pierdes, deberás generar uno nuevo en @BotFather.

2. **Chat IDs:** Los Chat IDs de grupos suelen empezar con `-100`. Los de usuarios individuales son números positivos.

3. **Permisos del bot:** El bot debe tener permisos para enviar mensajes en los grupos.

4. **Producción:** En producción, usa webhooks en lugar de polling para mejor performance. Consulta la documentación de Telegram Bot API.

5. **Backups:** Antes de aplicar migraciones en producción, haz un backup de la base de datos.

---

## 🎉 ¡Listo!

Ahora tienes un sistema de notificaciones de Telegram completamente funcional con arquitectura multi-tenant:

- ✅ Bot centralizado administrado por el superadmin
- ✅ Cada empresa configura sus propios chats
- ✅ Proceso simple para obtener Chat IDs
- ✅ Notificaciones automáticas cuando llegan emails
- ✅ Separación clara de responsabilidades

Si tienes problemas, revisa la sección de Troubleshooting o contacta al equipo de desarrollo.
