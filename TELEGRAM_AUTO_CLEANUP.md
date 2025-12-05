# Sistema Automático de Gestión de Chats de Telegram

## 🎯 Problema Resuelto

### Antes
- ❌ Los mensajes se enviaban **2 veces** (duplicados)
- ❌ Los chats de Telegram quedaban **huérfanos** al eliminar usuarios
- ❌ Se enviaban mensajes a chats de usuarios ya eliminados

### Ahora
- ✅ Los mensajes se envían **1 sola vez**
- ✅ Los chats se **eliminan automáticamente** al eliminar el usuario
- ✅ Solo se envían mensajes a usuarios activos con chat vinculado

---

## 🔧 Cambios Implementados

### 1. Eliminación de Duplicación de Envío

**Problema:** El sistema tenía 2 formas de enviar notificaciones:
- Signal automático (`post_save` de `ReceivedEmail`)
- Llamada manual en `imap_handler/services.py`

**Solución:** Eliminada la llamada manual, ahora solo usa el signal.

**Archivo modificado:** `app/imap_handler/services.py:394-396`

```python
# La notificación por Telegram se envía automáticamente via signal post_save
# Ver: telegram_bot/signals.py:send_telegram_alert_on_new_email
# NO llamar manualmente para evitar duplicados
```

---

### 2. Signal para Eliminar Chat al Eliminar Usuario

**Funcionalidad:** Cuando se elimina un usuario, su chat de Telegram se elimina automáticamente.

**Archivos creados:**
- `app/user/signals.py` - Signal `pre_delete` que elimina el chat
- Modificado `app/user/apps.py` - Importa los signals en `ready()`

**Cómo funciona:**
```python
@receiver(pre_delete, sender=User)
def delete_telegram_chat_on_user_delete(sender, instance, **kwargs):
    # Busca el chat de Telegram del usuario
    # Lo elimina automáticamente
```

**Flujo:**
```
Usuario eliminado → Signal pre_delete → Buscar chat → Eliminar chat de Telegram
```

---

### 3. Comando de Limpieza de Chats Huérfanos

**Comando:** `clean_orphan_chats`

**Ubicación:** `app/telegram_bot/management/commands/clean_orphan_chats.py`

**Uso:**
```bash
# Ver qué se eliminaría (sin cambios)
python manage.py clean_orphan_chats --dry-run

# Ejecutar limpieza (con confirmación)
python manage.py clean_orphan_chats

# Ejecutar sin confirmación
python manage.py clean_orphan_chats --force
```

**Lo que hace:**
1. Recorre todos los chats de Telegram
2. Para cada chat, busca si hay un usuario con ese `telegram_chat_id`
3. Si NO hay usuario → Chat huérfano → Se elimina
4. Muestra reporte de chats eliminados

**Ejemplo de salida:**
```
=== Limpieza de chats huérfanos ===
🗑️  Chat huérfano: Agus and Lucas (ID: -4817890724) | company | Sin usuario asociado
🗑️  Chat huérfano: s (ID: -4951834762) | company | Sin usuario asociado

✅ Eliminados 2 chats huérfanos
=== Resumen final ===
Total chats restantes: 1
Chats activos con email alerts: 1
```

---

## 📋 Flujo Completo de Gestión de Usuarios

### Crear Usuario con Telegram

**Admin Público → Empresas → Gestión de Usuarios → Crear Usuario**

1. Admin crea usuario y marca "Puede recibir alertas"
2. Sistema genera código de registro automáticamente
3. Admin comparte código con el usuario
4. Usuario ejecuta `/register CODIGO` en Telegram
5. Bot crea chat de Telegram y lo vincula al usuario
6. Usuario comienza a recibir alertas de email

**Resultado en BD:**
```
User:
  - email: juan@empresa.com
  - telegram_chat_id: "123456789"
  - can_receive_alerts: True

TelegramChat:
  - chat_id: 123456789
  - company: empresa
  - email_alerts: True
```

---

### Eliminar Usuario

**Admin → Usuarios → Eliminar usuario**

1. Admin elimina el usuario
2. **Signal automático se activa** (`pre_delete`)
3. Sistema busca el chat asociado al `telegram_chat_id`
4. **Chat se elimina automáticamente**
5. Usuario deja de recibir alertas

**Log del sistema:**
```
🗑️  Eliminando chat de Telegram Chat 123456789 asociado al usuario Juan Pérez
✅ Chat de Telegram eliminado exitosamente
```

---

### Deslinkear Usuario (Sin eliminarlo)

**Admin → Usuarios → Seleccionar → Acción: "Deslinkear cuentas de Telegram"**

1. Admin selecciona usuarios
2. Ejecuta acción "🔓 Deslinkear cuentas de Telegram"
3. Sistema:
   - Resetea `telegram_chat_id` del usuario
   - Elimina el chat de Telegram
   - Elimina códigos de registro usados y no usados
4. Usuario puede registrarse nuevamente con un nuevo código

**Ubicación del código:** `app/user/admin.py:257-310`

---

## 🧹 Mantenimiento y Limpieza

### Limpieza Manual de Chats Huérfanos

Si detectas que hay chats sin usuario asociado:

```bash
# Ver cuántos chats huérfanos hay
docker-compose exec web python manage.py clean_orphan_chats --dry-run

# Eliminarlos
docker-compose exec web python manage.py clean_orphan_chats --force
```

### Limpieza Programada (Opcional)

Puedes agregar una tarea de Celery Beat para limpiar automáticamente:

```python
# En settings.py - CELERY_BEAT_SCHEDULE
'cleanup-orphan-chats': {
    'task': 'telegram_bot.tasks.cleanup_orphan_chats_task',
    'schedule': crontab(hour=3, minute=0),  # Diario a las 3 AM
},
```

---

## ✅ Verificación del Sistema

### 1. Verificar que no hay duplicados

Envía un email de prueba y verifica los logs:

```bash
docker-compose logs -f celery | grep "DEBUG:"
```

**Deberías ver:**
```
🔍 DEBUG: Se encontraron 1 chats para company
🔍 DEBUG: Chat IDs: [6514522814]
🔍 DEBUG: Iteración 1/1 - Enviando a chat 6514522814
✅ DEBUG: Mensaje enviado exitosamente a 6514522814
```

**NO deberías ver:**
- Dos iteraciones para el mismo chat
- `_send_telegram_notification LLAMADO` dos veces

---

### 2. Verificar chats activos

```bash
docker-compose exec web python manage.py shell -c "
from telegram_bot.models import TelegramChat
chats = TelegramChat.objects.filter(email_alerts=True)
print(f'Chats con email alerts: {chats.count()}')
for chat in chats:
    print(f'  - {chat.name} ({chat.chat_id})')
"
```

---

### 3. Verificar eliminación automática

1. Crea un usuario de prueba con Telegram
2. Regístralo en Telegram
3. Verifica que aparece el chat: `TelegramChat.objects.count()`
4. Elimina el usuario desde el admin
5. Verifica que el chat se eliminó: `TelegramChat.objects.count()`

**Logs esperados:**
```
🗑️  Eliminando chat de Telegram ... asociado al usuario ...
✅ Chat de Telegram eliminado exitosamente
```

---

## 🆘 Problemas Comunes

### "Todavía veo mensajes duplicados"

**Causa:** Servicios no reiniciados después de los cambios

**Solución:**
```bash
docker-compose restart celery celery-beat web
```

---

### "Se envían mensajes a chats eliminados"

**Causa:** Chats huérfanos en la base de datos

**Solución:**
```bash
docker-compose exec web python manage.py clean_orphan_chats --force
```

---

### "El chat no se elimina al eliminar el usuario"

**Causa:** El signal no se está ejecutando

**Verificar:**
1. Que `user/apps.py` tiene el método `ready()` importando signals
2. Que el servicio `web` se reinició después del cambio
3. Revisar logs: `docker-compose logs web | grep "Eliminando chat"`

---

## 📊 Archivos Modificados/Creados

### Modificados
1. `app/imap_handler/services.py` - Eliminada llamada duplicada a `_send_telegram_notification()`
2. `app/user/apps.py` - Agregado `ready()` para importar signals
3. `app/telegram_bot/services.py` - Agregados logs de debug (opcionales, se pueden quitar)

### Creados
1. `app/user/signals.py` - Signal para eliminar chat al eliminar usuario
2. `app/telegram_bot/management/commands/clean_orphan_chats.py` - Comando de limpieza
3. Este documento (`TELEGRAM_AUTO_CLEANUP.md`)

---

## 🎯 Beneficios del Sistema

1. **Automatización:** Los chats se limpian automáticamente
2. **Consistencia:** No más chats huérfanos en la BD
3. **Eficiencia:** Solo se envía 1 mensaje por email (no duplicados)
4. **Escalabilidad:** Funciona con múltiples empresas y usuarios
5. **Mantenibilidad:** Comando de limpieza manual disponible si es necesario

---

## 🔮 Mejoras Futuras (Opcional)

1. **Limpieza programada:** Tarea de Celery Beat para limpiar chats huérfanos diariamente
2. **Notificación al admin:** Email cuando se detectan chats huérfanos
3. **Dashboard:** Vista en el admin mostrando estadísticas de chats activos/inactivos
4. **Soft delete:** Marcar chats como inactivos en lugar de eliminarlos (para auditoría)

---

**Última actualización:** 2025-01-20
**Versión:** 2.0
