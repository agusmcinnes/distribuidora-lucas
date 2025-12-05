# Guía de Gestión de Usuarios y Telegram

Esta guía explica las nuevas funcionalidades implementadas para gestionar usuarios y sus cuentas de Telegram.

## 🎯 Funcionalidades Implementadas

### 1. Deslinkear Cuentas de Telegram

Los administradores ahora pueden deslinkear cuentas de Telegram de usuarios directamente desde el admin.

**Ubicación:** Admin de Usuarios (tanto público como de tenant)

**Cómo usar:**
1. Ir a `/admin/` → Usuarios
2. Seleccionar uno o más usuarios que deseas deslinkear
3. En el menú de acciones, seleccionar **"🔓 Deslinkear cuentas de Telegram"**
4. Hacer clic en "Go"

**Qué hace:**
- Elimina el `telegram_chat_id` del usuario
- Elimina todos los chats de Telegram asociados
- Elimina los códigos de registro usados y no usados
- Permite que el usuario pueda registrarse nuevamente con un nuevo código

---

### 2. Gestión de Usuarios desde Admin Público

Los super administradores (en el esquema público) ahora pueden gestionar usuarios de cada empresa directamente desde la vista de edición de la empresa.

**Ubicación:** Admin Público → Empresas → [Seleccionar Empresa]

**Funcionalidades:**

#### Ver Usuarios de la Empresa
En la sección **"👥 Gestión de Usuarios"**, verás una tabla con:
- ID del usuario
- Nombre
- Email
- Rol (Manager, Supervisor, Cliente)
- Estado de Telegram (Vinculado, No vinculado)
- Código de registro activo (si existe)
- Estado (Activo/Inactivo)

#### Crear Nuevo Usuario
En la misma sección, encontrarás un formulario para crear usuarios:

**Campos:**
- **Nombre completo:** Nombre del usuario
- **Email:** Correo electrónico (debe ser único en la empresa)
- **Teléfono:** Opcional
- **Rol:** Seleccionar entre Manager, Supervisor, Cliente
- **Puede recibir alertas:** Checkbox (marcado por defecto)

**Proceso de creación:**
1. Llenar el formulario
2. Hacer clic en **"➕ Crear Usuario y Generar Código Telegram"**
3. El sistema:
   - Crea el usuario en el schema de la empresa
   - Si "Puede recibir alertas" está marcado:
     - Genera automáticamente un código de registro de Telegram
     - El código expira en 7 días
     - Asocia el código al usuario por email
4. Muestra un mensaje de éxito con el código generado

---

## 📋 Flujo Completo de Registro

### Escenario: Empresa Nueva con Usuario

#### Paso 1: Crear la Empresa
1. Ir a `/admin/` (esquema público)
2. Ir a **Empresas** → **Agregar Empresa**
3. Completar:
   - Nombre: "Mi Distribuidora"
   - Schema name: "mi_distribuidora"
   - Dominio: "midistribuidora.localhost"
   - Datos del admin (se crea automáticamente)
4. Guardar

#### Paso 2: Crear Usuario Adicional
1. Ir a **Empresas** → Buscar "Mi Distribuidora"
2. Hacer clic para editar
3. Scroll hasta **"👥 Gestión de Usuarios"**
4. Completar el formulario de nuevo usuario:
   - Nombre: "Juan Pérez"
   - Email: "juan@midistribuidora.com"
   - Rol: "Manager"
   - ✓ Puede recibir alertas
5. Hacer clic en "Crear Usuario y Generar Código Telegram"
6. **IMPORTANTE:** Copiar el código mostrado (ej: `A1B2C3D4`)

#### Paso 3: Configurar Telegram
1. Abrir Telegram
2. Buscar el bot de la empresa (configurado en TelegramConfig)
3. Si es chat de grupo:
   - Crear grupo
   - Agregar el bot al grupo
4. En el chat, escribir: `/register A1B2C3D4`
5. El bot confirma el registro
6. El usuario ahora recibirá alertas en ese chat

#### Paso 4: Verificar Vinculación
1. Volver a la página de edición de la empresa
2. En la tabla de usuarios, verificar que el estado de Telegram de Juan sea **"✓ Vinculado"**
3. El código ahora debe mostrar **"Código usado"**

---

## 🔄 Flujo de Desvinculación y Revinculación

### Escenario: Usuario necesita cambiar de chat

#### Paso 1: Deslinkear el Usuario
**Opción A - Desde Admin de Empresa (Tenant):**
1. Ir al dominio de la empresa (ej: `midistribuidora.localhost/admin/`)
2. Ir a **Usuarios**
3. Seleccionar el usuario (Juan Pérez)
4. Acciones → **"🔓 Deslinkear cuentas de Telegram"**
5. Confirmar

**Opción B - Desde Admin Público:**
1. Ir a `/admin/` (público)
2. Ir a **Empresas** → Editar "Mi Distribuidora"
3. En **"👥 Gestión de Usuarios"**, verás que Juan ya no tiene código activo
4. Puedes crear un nuevo código generando otro usuario o...
   - Ir al admin de **Códigos de Registro**
   - Crear nuevo código asignado a juan@midistribuidora.com

#### Paso 2: Generar Nuevo Código
Después de deslinkear, hay dos opciones:

**Opción A - Desde el admin de la empresa:**
1. Editar la empresa en admin público
2. En "Gestión de Usuarios", Juan ahora muestra "Sin código"
3. Ir a **Telegram Bot** → **Códigos de Registro** (en admin público)
4. Crear nuevo código:
   - Empresa: Mi Distribuidora
   - Asignar a: juan@midistribuidora.com
   - Nombre del usuario: Juan Pérez
5. Copiar el nuevo código generado

**Opción B - Eliminar y Recrear el Usuario:**
(No recomendado, ya que pierdes el historial)

#### Paso 3: Registrar Nuevo Chat
1. En Telegram, ir al nuevo chat/grupo
2. Escribir: `/register NUEVO_CODIGO`
3. Bot confirma el registro
4. Verificar en el admin que el estado sea "Vinculado"

---

## 🛠️ Solución de Problemas

### El código no funciona
**Verificar:**
- ✅ El código no está expirado (7 días desde creación)
- ✅ El código no fue usado anteriormente
- ✅ El bot está activo y funcionando
- ✅ El comando es `/register CODIGO` (sin espacios extras)

**Solución:**
- Generar un nuevo código desde el admin

### Usuario no recibe alertas
**Verificar:**
1. Estado de vinculación en la tabla de usuarios (debe ser "✓ Vinculado")
2. Campo "Puede recibir alertas" está marcado
3. El chat de Telegram está activo
4. El bot tiene permisos para enviar mensajes en el grupo

### No puedo crear usuario
**Posibles errores:**
- Email duplicado → Cambiar el email
- Rol no existe → Asegurarse de que los roles estén creados en el tenant
- Schema name incorrecto → Verificar que la empresa esté correctamente creada

---

## 🎨 Características Adicionales

### Tabla de Usuarios
La tabla muestra en tiempo real:
- **Código activo:** Se muestra en formato de código inline si existe
- **Estado Telegram:**
  - ✓ Vinculado (verde): Tiene chat vinculado vía código
  - ✓ Manual (verde): Tiene telegram_chat_id configurado manualmente
  - ✗ No vinculado (gris): Sin configuración de Telegram
- **Códigos expirados:** Se muestran en naranja
- **Códigos usados:** Se muestran en gris

### Seguridad
- Los códigos expiran en 7 días automáticamente
- Cada código solo puede usarse una vez
- Los códigos están asociados a un email específico
- Solo el super admin puede crear/eliminar usuarios cross-tenant

---

## 📊 Comandos de Verificación

### Verificar Estado del Bot
```bash
docker-compose exec web python manage.py test_telegram_bot --test-all
```

### Ver Chats Activos
```bash
# Desde admin público
/admin/ → Telegram Bot → Chats de Telegram
```

### Ver Códigos Generados
```bash
# Desde admin público
/admin/ → Telegram Bot → Códigos de Registro
# Filtrar por empresa o estado (usado/expirado)
```

---

## 🔗 Referencias

### Admin Público
- **URL:** `http://localhost:8000/admin/` o dominio público
- **Acceso:** Super administrador con permisos en esquema público
- **Gestiona:** Empresas, Dominios, Bots, Chats, Códigos de Registro

### Admin de Tenant
- **URL:** `http://[empresa].localhost:8000/admin/`
- **Acceso:** Administrador de la empresa específica
- **Gestiona:** Usuarios, Roles, Emails, Configuraciones IMAP de su empresa

---

## ✅ Checklist de Testing

Para probar el flujo completo:

- [ ] Crear empresa nueva desde admin público
- [ ] Verificar que el admin de la empresa se creó automáticamente
- [ ] Crear usuario adicional desde "Gestión de Usuarios"
- [ ] Copiar el código de Telegram generado
- [ ] Registrar el código en Telegram con `/register CODIGO`
- [ ] Verificar que el estado cambia a "Vinculado"
- [ ] Enviar un email de prueba y verificar que llega la alerta
- [ ] Deslinkear el usuario usando la acción del admin
- [ ] Verificar que el estado cambia a "No vinculado"
- [ ] Generar nuevo código y re-registrar
- [ ] Verificar que vuelve a funcionar

---

**Última actualización:** 2025-01-20
**Versión:** 1.0
