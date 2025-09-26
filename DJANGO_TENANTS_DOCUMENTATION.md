# Documentación del Sistema Django Tenants - Distribuidora Lucas

## Tabla de Contenidos
1. [Introducción](#introducción)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Configuración de Django Tenants](#configuración-de-django-tenants)
4. [Modelos y Esquema de Base de Datos](#modelos-y-esquema-de-base-de-datos)
5. [Middleware y Routing](#middleware-y-routing)
6. [Administración Cross-Tenant](#administración-cross-tenant)
7. [APIs y Vistas](#apis-y-vistas)
8. [Migraciones y Base de Datos](#migraciones-y-base-de-datos)
9. [Templates y Frontend](#templates-y-frontend)
10. [Flujo de Funcionamiento](#flujo-de-funcionamiento)
11. [Casos de Uso](#casos-de-uso)
12. [Mejores Prácticas](#mejores-prácticas)

## Introducción

El sistema utiliza **django-tenants** para implementar una arquitectura de multi-tenancy que permite que múltiples empresas distribuidoras compartan la misma aplicación pero mantengan sus datos completamente separados. Cada empresa (tenant) tiene su propio esquema de base de datos PostgreSQL.

### Versión Utilizada
- **django-tenants**: 3.6.1
- **Django**: 4.2.11
- **Base de datos**: PostgreSQL con backend específico de django-tenants

## Arquitectura del Sistema

### Esquemas de Base de Datos

El sistema utiliza dos tipos de esquemas:

1. **Esquema Público (`public`)**: Contiene datos compartidos entre todos los tenants
   - Modelos de Company (tenants)
   - Modelos de Domain
   - Configuración global del sistema

2. **Esquemas Privados**: Cada empresa tiene su propio esquema con sus datos específicos
   - Usuarios (`user`)
   - Emails recibidos (`emails`)
   - Configuración IMAP (`imap_handler`)
   - Configuración de Telegram (`telegram_bot`)

### Separación de Apps

#### Apps Compartidas (SHARED_APPS)
```python
SHARED_APPS = [
    "django_tenants",  # Debe ir PRIMERO
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions", 
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "company",  # Contiene el modelo tenant
]
```

#### Apps del Tenant (TENANT_APPS)
```python
TENANT_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "user",
    "emails", 
    "imap_handler",
    "telegram_bot",
]
```

## Configuración de Django Tenants

### Settings principales (`app/settings.py:264-276`)

```python
# Modelo de tenant
TENANT_MODEL = "company.Company"

# Modelo de dominio  
TENANT_DOMAIN_MODEL = "company.Domain"

# Router de base de datos
DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)

# Configuración del esquema público
PUBLIC_SCHEMA_NAME = "public"
PUBLIC_SCHEMA_URLCONF = "app.urls_public"
```

### Configuración de Base de Datos (`app/settings.py:104-113`)

```python
DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",  # Backend específico
        "NAME": os.getenv("POSTGRES_DB", "distribuidora_lucas"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}
```

### Middleware (`app/settings.py:70-79`)

```python
MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",  # DEBE ir PRIMERO
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

## Modelos y Esquema de Base de Datos

### Modelo Company (Tenant) (`app/company/models.py:5-40`)

```python
class Company(TenantMixin):
    """Modelo que representa una empresa distribuidora."""
    
    name = models.CharField(max_length=200, verbose_name="Nombre de la empresa")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Heredado de TenantMixin:
    # - schema_name: Nombre del esquema en PostgreSQL
    # - auto_create_schema: Se crea automáticamente el esquema
    # - auto_drop_schema: Se elimina automáticamente al borrar
```

**Campos principales:**
- `schema_name`: Nombre único del esquema PostgreSQL
- `name`: Nombre descriptivo de la empresa
- `is_active`: Estado de la empresa
- `created_at/updated_at`: Timestamps

### Modelo Domain (`app/company/models.py:42-46`)

```python
class Domain(DomainMixin):
    """Dominios asociados a cada tenant (empresa)"""
    pass
    
    # Heredado de DomainMixin:
    # - domain: El dominio (ej: empresa1.localhost)
    # - tenant: ForeignKey al Company
    # - is_primary: Si es el dominio principal
```

### Modelos de Tenant (Esquemas Privados)

#### User Model (`app/user/migrations/0001_initial.py:32-52`)
- Usuarios específicos de cada empresa
- Roles y permisos por empresa
- Chat IDs de Telegram por usuario
- Relación con Company a través del esquema

#### ReceivedEmail Model (`app/emails/migrations/0001_initial.py:18-41`)
- Emails procesados por empresa
- Prioridades y estados de procesamiento
- Asignación a usuarios específicos
- Timestamps de procesamiento

## Middleware y Routing

### TenantMainMiddleware

El middleware de Django Tenants (`django_tenants.middleware.main.TenantMainMiddleware`) es el componente central que:

1. **Analiza la request**: Extrae el dominio de la request HTTP
2. **Identifica el tenant**: Busca el Company asociado al dominio
3. **Cambia el esquema**: Configura la conexión de base de datos al esquema correcto
4. **Establece el contexto**: Hace disponible el tenant en `connection.tenant`

### URL Configuration

#### URLs Públicas (`app/urls_public.py`)
- Dashboard cross-tenant para super admin
- APIs para obtener datos de todos los tenants
- Admin del esquema público

#### URLs de Tenant (`app/urls.py`)
- Admin personalizado por empresa
- URLs específicas de cada tenant
- Telegram webhooks por empresa

### Personalización del Admin por Tenant (`app/urls.py:10-31`)

```python
def get_admin_titles():
    try:
        from django.db import connection
        tenant = connection.tenant
        company_name = tenant.name if hasattr(tenant, 'name') else "Empresa"
        return {
            'header': f"🚚 {company_name} - Sistema de Alertas",
            'title': f"{company_name} Admin", 
            'index': "Panel de Administración"
        }
    except:
        return {
            'header': "🚚 Distribuidora Lucas - Sistema de Alertas",
            'title': "Distribuidora Lucas Admin",
            'index': "Panel de Administración"
        }
```

## Administración Cross-Tenant

### CompanyAdmin (`app/company/admin.py:12-93`)

Permite gestionar todas las empresas desde el esquema público:

**Funcionalidades:**
- Listar todas las empresas con estadísticas
- Ver usuarios, emails y bots por tenant
- Gestionar dominios asociados
- Estados activo/inactivo

**Métodos destacados:**
- `get_tenant_users_count()`: Cuenta usuarios por tenant usando `tenant_context`
- `get_tenant_emails_count()`: Cuenta emails por tenant
- `get_telegram_bots_count()`: Cuenta bots de Telegram por tenant

### Super Admin Cross-Tenant (`app/company/super_admin.py`)

Clases de admin que permiten ver datos de todos los tenants:

#### CrossTenantEmailAdmin
- Lista emails de todas las empresas
- Solo lectura
- Incluye nombre del tenant

#### CrossTenantUserAdmin  
- Lista usuarios de todas las empresas
- Solo lectura
- Muestra relación con tenant

#### CrossTenantTelegramBotAdmin
- Lista bots de todas las empresas
- Solo lectura
- Información por tenant

## APIs y Vistas

### Dashboard Cross-Tenant (`app/company/views.py:8-61`)

```python
@staff_member_required
def cross_tenant_dashboard(request):
    """Dashboard con datos de todos los tenants"""
    data = []
    
    for company in Company.objects.filter(is_active=True).exclude(schema_name='public'):
        tenant_data = {
            'company': company,
            'users': 0,
            'emails': 0, 
            'telegram_bots': 0,
            'recent_emails': []
        }
        
        try:
            with tenant_context(company):
                # Acceso a datos específicos del tenant
                from django.contrib.auth.models import User
                tenant_data['users'] = User.objects.count()
                
                from emails.models import ReceivedEmail
                tenant_data['emails'] = ReceivedEmail.objects.count()
                # ... más lógica
        except Exception as e:
            tenant_data['error'] = str(e)
            
        data.append(tenant_data)
```

### APIs Cross-Tenant

#### cross_tenant_emails_api (`app/company/views.py:64-88`)
- Retorna emails de todos los tenants
- Formato JSON
- Limitado a 50 emails por tenant para performance

#### cross_tenant_users_api (`app/company/views.py:91-116`)
- Retorna usuarios de todos los tenants
- Información básica de usuarios
- Incluye tenant de origen

## Migraciones y Base de Datos

### Estructura de Migraciones

1. **company/migrations/0001_initial.py**: Crea modelos Company y Domain en esquema público
2. **user/migrations/0001_initial.py**: Crea modelos User y Role en esquemas de tenant
3. **emails/migrations/0001_initial.py**: Crea modelo ReceivedEmail en esquemas de tenant
4. **telegram_bot/migrations/0001_initial.py**: Crea modelos de bot en esquemas de tenant
5. **imap_handler/migrations/0001_initial.py**: Crea configuración IMAP en esquemas de tenant

### Comandos de Migración

```bash
# Migrar esquema público
python manage.py migrate_schemas --schema=public

# Migrar todos los esquemas de tenants
python manage.py migrate_schemas --tenant

# Migrar un tenant específico
python manage.py migrate_schemas --schema=empresa1
```

### Índices Importantes

En ReceivedEmail (`app/emails/migrations/0001_initial.py:39`):
```python
'indexes': [
    models.Index(fields=['company', 'status'], name='emails_rece_company_b1d8b8_idx'),
    models.Index(fields=['received_date'], name='emails_rece_receive_aac5e5_idx'),
    models.Index(fields=['status'], name='emails_rece_status_a82ed6_idx'),
    models.Index(fields=['priority'], name='emails_rece_priorit_1d63b3_idx'),
]
```

## Templates y Frontend

### Dashboard Cross-Tenant (`app/templates/admin/cross_tenant_dashboard.html`)

Template que muestra información consolidada de todos los tenants:

**Características:**
- Cards por empresa con estadísticas
- Lista de emails recientes por tenant
- Información de bots de Telegram
- Manejo de errores por tenant
- Resumen general consolidado

**Secciones principales:**
- Header con título del dashboard
- Cards individuales por empresa
- Estadísticas (usuarios, emails, bots)
- Listas de emails recientes
- Resumen general con totales

## Flujo de Funcionamiento

### 1. Request Incoming
```
Request: empresa1.localhost/admin/
  ↓
TenantMainMiddleware
  ↓
Lookup Domain: empresa1.localhost
  ↓
Find Company: empresa1
  ↓
Set schema: empresa1_schema
  ↓
connection.tenant = empresa1_company
  ↓
Route to tenant URLs
```

### 2. Tenant Context Usage

```python
# En esquema público
for company in Company.objects.all():
    with tenant_context(company):
        # Ahora estamos en el esquema de 'company'
        users = User.objects.all()  # Solo usuarios de esta empresa
        emails = ReceivedEmail.objects.all()  # Solo emails de esta empresa
```

### 3. Database Schema Switching

```sql
-- Automáticamente ejecutado por django-tenants
SET search_path TO empresa1_schema, public;

-- Ahora las queries van al esquema correcto
SELECT * FROM user_user;  -- user_user en empresa1_schema
SELECT * FROM emails_receivedemail;  -- emails_receivedemail en empresa1_schema
```

## Casos de Uso

### 1. Crear Nueva Empresa

```python
# 1. Crear el tenant
company = Company.objects.create(
    schema_name='nueva_empresa',
    name='Nueva Empresa S.A.',
    is_active=True
)

# 2. Crear dominio
Domain.objects.create(
    domain='nueva-empresa.localhost',
    tenant=company,
    is_primary=True
)

# 3. Migrar esquema (automático si auto_create_schema=True)
# El esquema se crea automáticamente con las migraciones
```

### 2. Acceder a Datos Cross-Tenant

```python
# Desde el esquema público
companies_data = []
for company in Company.objects.filter(is_active=True):
    with tenant_context(company):
        # Estamos ahora en el esquema de la empresa
        user_count = User.objects.count()
        email_count = ReceivedEmail.objects.count()
        
        companies_data.append({
            'company': company.name,
            'users': user_count,
            'emails': email_count
        })
```

### 3. Procesamiento de Emails por Tenant

```python
# En imap_handler/tasks.py (contexto de tenant)
def process_emails_for_tenant():
    # Los emails se procesan dentro del contexto del tenant actual
    emails = ReceivedEmail.objects.filter(status='pending')
    
    for email in emails:
        # Procesar email específico del tenant
        users = User.objects.filter(can_receive_alerts=True)
        # Enviar alertas solo a usuarios de este tenant
```

### 4. Admin Personalizado por Tenant

```python
# El admin se personaliza automáticamente por tenant
def get_admin_titles():
    tenant = connection.tenant  # Tenant actual basado en dominio
    return f"{tenant.name} - Admin"
```

## Mejores Prácticas

### 1. Uso de tenant_context

```python
# ✅ Correcto
with tenant_context(company):
    users = User.objects.all()

# ❌ Incorrecto - puede acceder a datos incorrectos
users = User.objects.all()  # Sin contexto específico
```

### 2. Manejo de Errores Cross-Tenant

```python
for company in Company.objects.all():
    try:
        with tenant_context(company):
            # Operaciones con el tenant
            data = process_tenant_data()
    except Exception as e:
        # Log del error específico del tenant
        logger.error(f"Error en tenant {company.name}: {e}")
        continue  # Continuar con otros tenants
```

### 3. Performance en Operaciones Cross-Tenant

```python
# ✅ Limitar datos para performance
with tenant_context(company):
    recent_emails = ReceivedEmail.objects.order_by('-created_at')[:50]

# ✅ Usar select_related/prefetch_related
companies = Company.objects.select_related().prefetch_related('domains')
```

### 4. Migraciones

```bash
# Siempre migrar esquema público primero
python manage.py migrate_schemas --schema=public

# Luego migrar todos los tenants
python manage.py migrate_schemas --tenant
```

### 5. Testing

```python
# Para tests, usar TenantTestCase
from django_tenants.test.cases import TenantTestCase

class MyTenantTest(TenantTestCase):
    def test_tenant_specific_functionality(self):
        # El test se ejecuta en un tenant temporal
        user = User.objects.create(name='Test User')
        self.assertEqual(user.name, 'Test User')
```

## Consideraciones de Seguridad

1. **Aislamiento de Datos**: Los datos están completamente aislados por esquema
2. **Validación de Dominios**: Solo dominios registrados pueden acceder
3. **Cross-Tenant Access**: Solo disponible para super admins en esquema público
4. **Middleware Order**: TenantMainMiddleware DEBE ir primero
5. **Schema Validation**: Django Tenants valida nombres de esquema automáticamente

## Troubleshooting Común

### Error: "No tenant for hostname"
- Verificar que el dominio esté registrado en el modelo Domain
- Verificar que is_primary=True en el dominio principal

### Error: "relation does not exist"
- Ejecutar migraciones en el esquema correcto
- Verificar que la app esté en TENANT_APPS

### Performance Issues en Cross-Tenant
- Limitar cantidad de datos por tenant
- Usar paginación en dashboards
- Implementar cache para datos estáticos

### Migrations Issues
- Migrar esquema público primero
- Verificar que las apps estén correctamente categorizadas en SHARED_APPS y TENANT_APPS