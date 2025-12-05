# Distribuidora Lucas - Sistema de Alertas de Email

## Descripción General

Sistema automatizado multi-tenant para procesamiento de emails IMAP y envío de alertas vía Telegram. Diseñado para distribuidoras que necesitan mantener al equipo informado sobre nuevos pedidos, consultas y comunicaciones importantes.

## Tecnologías Principales

- **Framework**: Django 4.2.11
- **Base de Datos**: PostgreSQL 15 con django-tenants 3.6.1
- **Procesamiento Asíncrono**: Celery 5.4.0 + Redis 5.2.1
- **Multi-tenancy**: django-tenants (esquemas PostgreSQL)
- **Notificaciones**: Telegram Bot API
- **Containerización**: Docker + Docker Compose
- **Python**: 3.11

## Arquitectura del Proyecto

### Multi-Tenancy

El proyecto utiliza django-tenants para soportar múltiples empresas (tenants) en una sola instalación:

- **Esquema Público (public)**: Contiene datos compartidos entre todos los tenants
  - Empresas (Company)
  - Dominios (Domain)
  - Configuración de Telegram (TelegramConfig, TelegramChat, TelegramMessage)
  - Códigos de Registro (TelegramRegistrationCode)

- **Esquemas Privados**: Cada empresa tiene su propio esquema con:
  - Usuarios (User)
  - Emails recibidos (ReceivedEmail)
  - Configuraciones IMAP (IMAPConfiguration)

### Flujo de Datos

```
📧 Email IMAP → Celery Task → Procesamiento → Clasificación por Prioridad
                                                          ↓
                                               🤖 Telegram Alert → Chat específico del Tenant
                                                          ↓
                                               📊 Registro en BD (por tenant)
```

## Estructura de Aplicaciones

### `company/` (SHARED_APP)
Gestión de empresas y multi-tenancy.

**Modelos principales:**
- `Company(TenantMixin)`: Representa cada distribuidora/tenant
  - Campos: name, schema_name, created_at, is_active
  - Métodos: get_active_users_count()
- `Domain(DomainMixin)`: Dominios asociados a cada tenant

**Admin:**
- `SuperAdminSite`: Admin para esquema público (gestión de empresas)
- `TenantAdminSite`: Admin para esquemas privados (gestión interna)
- Middleware: `TenantAdminMiddleware` - Configura admin según esquema actual

**Comandos:**
- `create_company`: Crear nueva empresa/tenant

### `user/` (TENANT_APP)
Gestión de usuarios dentro de cada tenant.

**Modelos:**
- `Role`: Roles del sistema (manager, supervisor, client)
- `User`: Usuarios de la empresa
  - Campos: name, email, phone_number, telegram_chat_id, role, company
  - Métodos: is_manager(), is_supervisor(), has_telegram()

**Nota:** Los usuarios son específicos de cada tenant (esquema privado).

### `emails/` (TENANT_APP)
Almacenamiento y tracking de emails recibidos.

**Modelos:**
- `ReceivedEmail`: Email procesado
  - Estados: pending, processing, sent, failed, ignored
  - Prioridades: low, medium, high, critical
  - Campos: sender, subject, body, received_date, priority, status, assigned_to
  - Métodos: mark_as_sent(), mark_as_failed(), assign_to_user()

### `imap_handler/` (TENANT_APP)
Procesamiento de emails IMAP.

**Modelos:**
- `IMAPConfiguration`: Configuración de cuentas IMAP
  - Campos: host, port, username, password, use_ssl, inbox_folder, check_interval
  - Métodos: is_due_for_check(), mark_as_checked()

- `EmailProcessingRule`: Reglas automáticas de procesamiento
  - Criterios: subject_contains, sender_contains, body_contains, regex
  - Acciones: asignar prioridad, asignar a rol

- `IMAPProcessingLog`: Logs de procesamiento

**Servicios:**
- `app/imap_handler/services.py`: Lógica de conexión y procesamiento IMAP

**Comandos:**
- `process_imap_emails`: Procesar emails manualmente
- `test_imap_connection`: Probar conexión IMAP
- `auto_process`: Procesamiento automático

**Tareas Celery:**
- `process_imap_emails_task`: Tarea periódica (cada 300s por defecto)

### `telegram_bot/` (SHARED_APP)
Bot de Telegram centralizado para todas las empresas.

**Modelos:**
- `TelegramConfig`: Configuración del bot
  - Campos: name, bot_token, is_active

- `TelegramChat`: Chats donde enviar alertas
  - Tipos: private, group, supergroup, channel
  - Niveles de alerta: high, medium, low, all
  - Campos: company (FK), bot (FK), chat_id, alert_level, email_alerts, system_alerts

- `TelegramMessage`: Registro de mensajes enviados
  - Estados: pending, sent, failed, retry
  - Tipos: email_alert, system_alert, manual
  - Campos: company (FK), chat (FK), subject, message, status, telegram_message_id

- `TelegramRegistrationCode`: Códigos para registro de chats
  - Campos: code (8 caracteres), company (FK), expires_at, is_used
  - Métodos: generate_unique_code(), is_valid(), mark_as_used()

**Servicios:**
- `app/telegram_bot/services.py`: Lógica del bot y envío de mensajes

**Comandos:**
- `run_telegram_bot`: Ejecutar bot en modo polling
- `setup_telegram`: Configurar bot
- `test_telegram_bot`: Probar bot
- `sync_telegram_config`: Sincronizar configuración

**Arquitectura del Bot:**
- Un único bot puede manejar múltiples empresas
- Cada chat está asociado a una empresa específica
- Sistema de códigos de registro para facilitar onboarding
- Niveles de alerta configurables por chat

## Configuración de Docker

### Servicios

1. **db** (PostgreSQL 15)
   - Puerto: 5432 (interno)
   - Database: distribuidora_lucas

2. **redis** (Redis 7)
   - Puerto: 6379 (interno)
   - Broker para Celery

3. **web** (Django)
   - Puerto: 8000:8000
   - Comando: `runserver 0.0.0.0:8000`

4. **celery** (Worker)
   - Procesa tareas asíncronas

5. **celery-beat** (Scheduler)
   - Programa tareas periódicas

6. **telegram-bot**
   - Ejecuta bot en modo daemon
   - Restart: unless-stopped

### Variables de Entorno

Ver `.env.example` para configuración completa.

**Esenciales:**
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `IMAP_HOST`, `IMAP_PORT`, `IMAP_EMAIL`, `IMAP_PASSWORD`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_DEFAULT_CHAT_ID`

## Clasificación de Prioridades

El sistema clasifica automáticamente emails basándose en palabras clave:

**Alta Prioridad:**
- venta, urgente, importante, alerta, crítico, error

**Media Prioridad:**
- pedido, orden, consulta, información

**Baja Prioridad:**
- newsletter, promoción, marketing, notificación

Configurables en settings.py: `HIGH_PRIORITY_KEYWORDS`, `MEDIUM_PRIORITY_KEYWORDS`, `LOW_PRIORITY_KEYWORDS`

## Comandos de Gestión Útiles

### Tenant Management
```bash
# Crear nueva empresa/tenant
python manage.py create_company

# Migrar todos los tenants
python manage.py migrate_schemas
```

### IMAP
```bash
# Probar conexión IMAP
python manage.py test_imap_connection

# Procesar emails manualmente
python manage.py process_imap_emails
```

### Telegram
```bash
# Configurar bot
python manage.py setup_telegram --token "TOKEN" --chat-id CHAT_ID

# Probar bot
python manage.py test_telegram_bot --test-all

# Ejecutar bot (polling mode)
python manage.py run_telegram_bot --daemon

# Sincronizar configuración
python manage.py sync_telegram_config
```

### Docker
```bash
# Iniciar sistema completo
docker-compose up -d

# Ver logs
docker-compose logs -f [servicio]

# Ejecutar migraciones
docker-compose exec web python manage.py migrate_schemas

# Crear superusuario
docker-compose exec web python manage.py createsuperuser
```

## Admin

El sistema tiene dos interfaces de admin separadas:

1. **Admin Público** (`/admin/`): Gestión de empresas, dominios, bots de Telegram
2. **Admin Tenant** (según dominio): Gestión interna de usuarios, emails, configuraciones IMAP

El middleware `TenantAdminMiddleware` (company/middleware.py:73) determina qué admin mostrar según el esquema activo.

## Archivos de Configuración Clave

- `app/app/settings.py`: Configuración Django y tenants
- `app/app/urls.py`: URLs para tenants
- `app/app/urls_public.py`: URLs para esquema público
- `app/app/celery.py`: Configuración Celery
- `docker-compose.yml`: Servicios Docker
- `Dockerfile`: Imagen Python 3.11 con dependencias
- `requirements.txt`: Dependencias Python

## Logs

- Ubicación: `app/logs/`
- Configuración en `settings.py:224-260`
- Logger principal: `imap_handler`
- Niveles: DEBUG, INFO, WARNING, ERROR

## Seguridad

- App Passwords para Gmail (no contraseña normal)
- Tokens secretos para webhooks de Telegram
- Validación de orígenes en webhooks
- Separación de datos por tenant (esquemas PostgreSQL)
- SECRET_KEY en variables de entorno

## Notas de Desarrollo

### Cross-Schema Relationships
- Evitar ForeignKeys directos entre SHARED_APPS y TENANT_APPS
- Usar campos de texto para referencias (ej: `assigned_to_user_email` en TelegramRegistrationCode)
- Usar `tenant_context` para consultas cross-schema

### Testing
- Los tests deben considerar multi-tenancy
- Crear tenants de prueba para tests de TENANT_APPS

### Migraciones
- Usar `migrate_schemas` en lugar de `migrate`
- Las migraciones de SHARED_APPS van al esquema público
- Las migraciones de TENANT_APPS se ejecutan en cada esquema privado

## Estado Actual del Proyecto

Según git status (branch: develop):
- Sistema funcional con django-tenants implementado
- Telegram bot con sistema de códigos de registro
- Múltiples migraciones pendientes de commit
- Admin separado para public/tenant schemas

### Últimas Funcionalidades Agregadas (2025-01-20)

#### 1. Desvinculación de Cuentas de Telegram
- **Ubicación:** `app/user/admin.py:257-310`
- **Acción:** `unlink_telegram`
- **Funcionalidad:**
  - Resetea `telegram_chat_id` del usuario
  - Elimina chats de Telegram asociados vía códigos de registro
  - Elimina códigos de registro (usados y no usados)
  - Permite re-registro con nuevo código

#### 2. Gestión de Usuarios desde Admin Público
- **Ubicación:** `app/company/admin.py`
- **Componentes:**
  - `manage_users_display()` (línea 193): Muestra tabla de usuarios con estado de Telegram
  - `changeform_view()` (línea 394): Override para manejar POST de creación
  - `_handle_create_user()` (línea 401): Crea usuarios cross-schema con códigos de Telegram

- **Características:**
  - Vista de todos los usuarios de una empresa desde admin público
  - Tabla interactiva con:
    - Estado de vinculación Telegram
    - Códigos de registro activos
    - Información de roles y contacto
  - Formulario inline para crear usuarios directamente
  - Generación automática de códigos de Telegram al crear usuario
  - Gestión cross-schema con manejo seguro de conexiones

#### 3. Helpers para Telegram
- `_get_telegram_code_for_user()` (línea 325): Obtiene código activo del usuario
- `_get_telegram_status()` (línea 351): Verifica estado de vinculación
- `_get_csrf_token()` (línea 318): Helper para tokens CSRF en formularios inline

### Flujo de Trabajo Mejorado

**Creación de Usuario con Telegram:**
1. Admin público → Empresas → [Seleccionar Empresa]
2. Sección "Gestión de Usuarios" muestra usuarios actuales
3. Formulario inline para crear nuevo usuario
4. Sistema genera automáticamente código de registro
5. Usuario usa `/register CODIGO` en Telegram
6. Estado actualiza a "Vinculado" automáticamente

**Desvinculación y Revinculación:**
1. Seleccionar usuario en admin
2. Acción "Deslinkear cuentas de Telegram"
3. Sistema limpia toda la data de Telegram
4. Generar nuevo código desde admin público
5. Usuario se registra nuevamente con nuevo código

Ver `TELEGRAM_USER_MANAGEMENT_GUIDE.md` para instrucciones detalladas.

## Referencias Rápidas

### Modelos por Schema

**Public Schema (SHARED_APPS):**
- company.Company
- company.Domain
- telegram_bot.TelegramConfig
- telegram_bot.TelegramChat
- telegram_bot.TelegramMessage
- telegram_bot.TelegramRegistrationCode

**Tenant Schema (TENANT_APPS):**
- user.User
- user.Role
- emails.ReceivedEmail
- imap_handler.IMAPConfiguration
- imap_handler.EmailProcessingRule
- imap_handler.IMAPProcessingLog

### Rutas de Archivos Importantes

- Modelos: `app/{app_name}/models.py`
- Admin: `app/{app_name}/admin.py`
- Servicios: `app/{app_name}/services.py`
- Tasks: `app/{app_name}/tasks.py`
- Comandos: `app/{app_name}/management/commands/`
