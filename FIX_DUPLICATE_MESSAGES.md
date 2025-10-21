# Solución para Mensajes Duplicados de Email en Telegram

## 🔍 Problema Identificado

Los mensajes de email se están enviando **2 veces** por Telegram porque tienes **2 chats registrados** para la misma empresa con alertas de email activadas.

El sistema está diseñado para enviar a **todos** los chats activos de una empresa, por eso ves duplicados.

## 📋 Diagnóstico

### Paso 1: Verificar Chats Duplicados

Ejecuta el comando de diagnóstico:

```bash
# Desde Docker
docker-compose exec web python manage.py check_duplicate_chats

# Desde local
cd app
python manage.py check_duplicate_chats
```

**Esto te mostrará:**
- Cuántos chats duplicados tienes
- Qué chat_ids están duplicados
- Cuáles tienen email alerts activos

**Ejemplo de salida:**
```
=== Verificando chats duplicados ===

⚠️  Encontrados 1 chat_ids duplicados:

📱 Chat ID: 123456789 (2 registros)
  - ID: 5 | Mi Chat | Mi Empresa | ✓ Activo | 📧 Email alerts ON
  - ID: 3 | Mi Chat | Mi Empresa | ✓ Activo | 📧 Email alerts ON

=== Chats activos con alertas de email ===

📱 Mi Chat (ID: 123456789) | Mi Empresa | Bot: Default Bot
📱 Mi Chat (ID: 123456789) | Mi Empresa | Bot: Default Bot

=== Resumen ===
Total chats: 2
Chats activos: 2
Chats con email alerts: 2
Chats activos con email alerts: 2  <-- ⚠️ ESTE ES EL PROBLEMA
```

Si ves **2 o más** chats activos con email alerts para la misma empresa, tienes duplicados.

---

## 🛠️ Solución

Tienes **3 opciones** para resolver esto:

### Opción 1: Limpieza Automática (Recomendado)

Este comando elimina automáticamente los duplicados, manteniendo solo el chat más reciente:

```bash
# Ver qué se eliminaría (sin hacer cambios)
docker-compose exec web python manage.py clean_duplicate_chats --dry-run

# Ejecutar la limpieza (con confirmación)
docker-compose exec web python manage.py clean_duplicate_chats

# Ejecutar sin confirmación
docker-compose exec web python manage.py clean_duplicate_chats --force
```

**Lo que hace:**
- Encuentra todos los chat_ids duplicados
- Mantiene el chat más reciente
- Elimina los chats duplicados
- Re-asigna códigos de registro si es necesario

---

### Opción 2: Desactivar Email Alerts en Uno de los Chats

Si quieres mantener ambos chats pero que solo uno reciba emails:

1. Ir al admin: `/admin/` → **Telegram Bot** → **Chats de Telegram**
2. Encontrar los chats duplicados (mismo chat_id)
3. Editar uno de ellos
4. **Desmarcar** la opción **"Email alerts"**
5. Guardar

Ahora solo un chat recibirá alertas de email.

---

### Opción 3: Eliminar Manualmente desde el Admin

1. Ir al admin: `/admin/` → **Telegram Bot** → **Chats de Telegram**
2. Seleccionar los chats duplicados
3. En **Acciones**, seleccionar **"Eliminar chats de telegram seleccionados"**
4. Confirmar

---

## ✅ Verificación

Después de aplicar la solución, verifica que solo haya un chat:

```bash
docker-compose exec web python manage.py check_duplicate_chats
```

**Salida esperada:**
```
=== Verificando chats duplicados ===

✅ No hay chats duplicados

=== Chats activos con alertas de email ===

📱 Mi Chat (ID: 123456789) | Mi Empresa | Bot: Default Bot

=== Resumen ===
Total chats: 1
Chats activos: 1
Chats con email alerts: 1
Chats activos con email alerts: 1  <-- ✅ CORRECTO
```

---

## 🔒 Prevención de Duplicados (Ya Implementado)

Se ha actualizado el código para **prevenir** que se registren chats duplicados en el futuro.

**Cambios implementados:**

### 1. Validación Mejorada en Registro

Ahora el comando `/register` valida:

- ✅ No permite registrar el mismo `chat_id` dos veces para la misma empresa
- ✅ No permite registrar un `chat_id` que ya pertenece a otra empresa
- ✅ Mensajes de error claros explicando el problema

**Ubicación:** `app/telegram_bot/services.py:503-526`

### 2. Mensajes de Error Mejorados

**Si intentas registrar un chat ya registrado para tu empresa:**
```
❌ Este chat ya está registrado como "Mi Chat" para tu empresa.

💡 Si quieres actualizar la configuración, elimina el chat antiguo desde el admin primero.
```

**Si intentas registrar un chat que pertenece a otra empresa:**
```
❌ Este chat ya está registrado para la empresa "Otra Empresa".

Un chat no puede estar registrado en múltiples empresas.
```

---

## 📊 Cómo Ocurrieron los Duplicados

Los duplicados pueden ocurrir por:

1. **Registrar el mismo código dos veces** (antes de la validación mejorada)
2. **Usar dos códigos diferentes** para el mismo chat_id
3. **Error manual** al crear chats desde el admin

Con las nuevas validaciones, esto **ya no puede pasar**.

---

## 🧪 Prueba Completa

Después de limpiar los duplicados:

1. **Enviar un email de prueba** a tu cuenta IMAP configurada
2. **Verificar en Telegram** que recibes **solo 1 mensaje**
3. **Revisar el admin** → **Telegram Bot** → **Mensajes de Telegram**
   - Deberías ver **solo 1 mensaje** enviado

---

## 📝 Resumen de Archivos Modificados

### Comandos Nuevos:
1. **`check_duplicate_chats.py`** - Diagnosticar duplicados
2. **`clean_duplicate_chats.py`** - Limpiar duplicados automáticamente

### Código Actualizado:
1. **`telegram_bot/services.py`** - Validación mejorada en registro

### Documentación:
1. Este archivo (`FIX_DUPLICATE_MESSAGES.md`)

---

## 🆘 Problemas Comunes

### "Todavía veo mensajes duplicados después de limpiar"

**Posibles causas:**
1. Los cambios no se aplicaron correctamente
2. Tienes múltiples empresas con chats registrados
3. El procesamiento de emails está corriendo en múltiples workers

**Solución:**
```bash
# Reiniciar todos los servicios
docker-compose restart

# Verificar de nuevo
docker-compose exec web python manage.py check_duplicate_chats
```

### "No puedo registrar mi chat después de limpiar"

**Causa:** El chat antiguo todavía existe en la BD

**Solución:**
```bash
# Verificar chats actuales
docker-compose exec web python manage.py check_duplicate_chats

# Si el chat todavía aparece, elimínalo desde el admin:
# /admin/ → Telegram Bot → Chats de Telegram → Eliminar
```

---

## 📞 Soporte

Si después de seguir estos pasos aún tienes duplicados:

1. Ejecuta: `docker-compose exec web python manage.py check_duplicate_chats`
2. Copia la salida completa
3. Revisa los logs del bot: `docker-compose logs telegram-bot`
4. Verifica que solo haya un servicio de bot corriendo: `docker-compose ps`

---

**Última actualización:** 2025-01-20
**Versión:** 1.0
