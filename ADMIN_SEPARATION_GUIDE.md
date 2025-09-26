# Separación de Administración: Super Admin vs Admin de Empresa

## Resumen

Se ha implementado una separación completa entre el **Super Admin** (esquema público) y el **Admin de Empresa** (esquemas de tenant). Cada uno tiene funcionalidades y permisos completamente diferentes.

## Tipos de Administrador

### 🏢 Super Admin (Esquema Público)
**URL de acceso**: `http://localhost/admin/`

**Funcionalidades EXCLUSIVAS**:
- ✅ **Crear nuevas empresas** con tenant completo
- ✅ **Ver dashboard cross-tenant** con datos de todas las empresas
- ✅ **Gestionar dominios** de todas las empresas
- ✅ **Ver usuarios de todas las empresas** (solo lectura)
- ✅ **Ver emails de todas las empresas** (solo lectura)
- ✅ **Ver bots de Telegram de todas las empresas** (solo lectura)
- ✅ **Estadísticas consolidadas** del sistema completo

**NO puede**:
- ❌ Gestionar datos específicos de una empresa
- ❌ Acceder a las URLs de tenant individuales
- ❌ Modificar contenido de emails o usuarios específicos

### 🏬 Admin de Empresa (Esquema Tenant)
**URL de acceso**: `http://empresa.localhost/admin/`

**Funcionalidades EXCLUSIVAS**:
- ✅ **Gestionar usuarios** de SU empresa únicamente
- ✅ **Ver y gestionar emails** de SU empresa únicamente
- ✅ **Configurar IMAP** de SU empresa
- ✅ **Configurar bot de Telegram** de SU empresa
- ✅ **Gestionar roles** dentro de SU empresa
- ✅ **Panel personalizado** con el nombre de SU empresa

**NO puede**:
- ❌ Ver datos de otras empresas
- ❌ Crear nuevas empresas
- ❌ Gestionar tenants o dominios
- ❌ Acceder a funcionalidades cross-tenant
- ❌ Ver el dashboard multi-tenant

## Arquitectura de Separación

### Middleware de Separación (`company/middleware.py`)

```python
class TenantAdminMiddleware:
    """
    Configura automáticamente el admin según el esquema activo
    """
    
    def _configure_public_admin(self):
        # Registra Company, Domain, CrossTenantAdmin
        # Template: admin/index.html (con estadísticas)
        
    def _configure_tenant_admin(self):
        # Desregistra Company, Domain
        # Template: admin/tenant_index.html (específico empresa)
        # Títulos personalizados por empresa
```

### Decoradores de Protección (`company/decorators.py`)

```python
@public_schema_required
def cross_tenant_dashboard(request):
    # Solo accesible desde esquema público
    
@tenant_schema_required  
def tenant_specific_view(request):
    # Solo accesible desde esquemas de tenant
```

### Registro Condicional de Admins

- **Esquema Público**: Se registran `CompanyAdmin`, `DomainAdmin` y cross-tenant admins
- **Esquemas Tenant**: Se desregistran modelos de tenant management

## Flujo de Acceso

### Super Admin
```
1. Usuario accede a http://localhost/admin/
2. TenantMainMiddleware detecta esquema 'public'
3. TenantAdminMiddleware configura admin para super admin
4. Se muestran opciones de gestión de tenants
5. Template admin/index.html con estadísticas cross-tenant
```

### Admin de Empresa
```
1. Usuario accede a http://empresa.localhost/admin/
2. TenantMainMiddleware detecta esquema 'empresa'
3. TenantAdminMiddleware configura admin para tenant
4. Se ocultan opciones de gestión de tenants
5. Template admin/tenant_index.html específico de empresa
```

## Diferencias en la Interfaz

### Super Admin Interface
- **Header**: "🏢 Distribuidora Lucas - Super Admin"
- **Dashboard**: Estadísticas de todas las empresas
- **Acciones**: Crear empresas, ver cross-tenant dashboard
- **Modelos visibles**: Company, Domain, + cross-tenant views

### Empresa Interface  
- **Header**: "🏢 [Nombre Empresa] - Panel de Administración"
- **Dashboard**: Funcionalidades específicas de la empresa
- **Acciones**: Gestionar usuarios, emails, configuración
- **Modelos visibles**: User, Role, ReceivedEmail, TelegramConfig, IMAPConfiguration

## Seguridad Implementada

### Protección por Esquema
```python
# Vistas protegidas que solo funcionan en esquema público
@public_schema_required
def cross_tenant_dashboard(request):
    # Si se accede desde tenant: HTTP 404

# Vistas protegidas que solo funcionan en esquemas tenant  
@tenant_schema_required
def tenant_specific_view(request):
    # Si se accede desde público: HTTP 404
```

### Validación de Permisos
- **Super Admin**: Requiere `is_superuser=True` + esquema público
- **Admin Empresa**: Requiere `is_staff=True` + esquema correcto de empresa
- **URLs Cross-tenant**: Protegidas con decoradores específicos

### Aislamiento de Datos
- **Base de datos**: Cada empresa tiene su esquema PostgreSQL separado
- **Admin Registry**: Modelos registrados dinámicamente según esquema
- **Templates**: Diferentes templates según tipo de admin
- **URLs**: URLs cross-tenant solo disponibles en esquema público

## Archivos Modificados/Creados

```
app/
├── company/
│   ├── middleware.py           # ✨ Middleware de separación de admin
│   ├── decorators.py           # ✨ Decoradores de protección
│   ├── tenant_admin.py         # ✨ Admin específico para tenants
│   ├── admin.py               # ✨ Registro condicional removido
│   └── apps.py                # ✨ Simplificado
├── templates/admin/
│   ├── index.html             # ✨ Super admin con estadísticas
│   └── tenant_index.html      # ✨ Admin de empresa específico
└── app/
    ├── settings.py            # ✨ Middleware agregado
    └── urls.py                # ✨ Simplificado
```

## Casos de Uso

### Crear Nueva Empresa (Solo Super Admin)
1. Super admin accede a `http://localhost/admin/`
2. Ve el botón "🏢 Crear Nueva Empresa"
3. Completa formulario con datos de empresa y admin
4. Sistema crea tenant + dominio + usuario automáticamente
5. Nueva empresa ya puede acceder a `http://nuevaempresa.localhost/admin/`

### Gestionar Empresa (Solo Admin de Empresa)
1. Admin empresa accede a `http://suempresa.localhost/admin/`
2. Ve panel personalizado con nombre de SU empresa
3. Puede gestionar usuarios, emails, configuración de SU empresa
4. NO ve opciones para crear empresas o ver otras empresas
5. Datos completamente aislados de otras empresas

### Ver Todas las Empresas (Solo Super Admin)
1. Super admin accede a dashboard cross-tenant
2. Ve estadísticas consolidadas de todas las empresas
3. Puede acceder directamente al admin de cualquier empresa
4. Datos de solo lectura para monitoreo general

## Ventajas de Esta Separación

### ✅ Seguridad
- **Aislamiento completo** de datos por empresa
- **Prevención de acceso cruzado** entre empresas
- **Control granular** de permisos por esquema

### ✅ Usabilidad
- **Interfaces específicas** para cada tipo de usuario
- **Sin confusión** entre funcionalidades de super admin y empresa
- **Navegación clara** y contextual

### ✅ Escalabilidad
- **Fácil agregar nuevas empresas** sin afectar existentes
- **Configuración automática** del admin por empresa
- **Mantenimiento simplificado** del código

### ✅ Mantenimiento
- **Separación clara** de responsabilidades
- **Código organizado** por contexto
- **Fácil debugging** por esquema específico

## Troubleshooting

### Error: "Esta página no está disponible en el contexto de empresa"
**Causa**: Intentas acceder a una URL de super admin desde un tenant
**Solución**: Accede desde `http://localhost/admin/` (esquema público)

### Error: Company/Domain no aparece en admin de tenant
**Causa**: Es comportamiento esperado, estos modelos solo están en super admin
**Solución**: Para gestionar tenants, usar el super admin

### Error: No veo estadísticas cross-tenant
**Causa**: No estás en el esquema público o no eres superusuario
**Solución**: Acceder como superusuario desde `http://localhost/admin/`

### Admin de empresa no se personaliza
**Causa**: El middleware no se está ejecutando correctamente
**Solución**: Verificar que `TenantAdminMiddleware` esté en `MIDDLEWARE` en `settings.py`

## Comandos Útiles

### Verificar esquema activo:
```python
from django.db import connection
print(f"Esquema actual: {connection.schema_name}")
```

### Verificar modelos registrados en admin:
```python
from django.contrib import admin
print("Modelos registrados:", list(admin.site._registry.keys()))
```

### Crear superusuario en esquema público:
```bash
python manage.py createsuperuser
```

### Crear superusuario en esquema de tenant:
```bash
python manage.py tenant_command createsuperuser --schema=empresa1
```

## Próximos Pasos

1. **Implementar roles más granulares** dentro de cada empresa
2. **Agregar auditoría** de acciones por empresa
3. **Personalizar más templates** por empresa
4. **Implementar notificaciones** específicas por contexto
5. **Agregar reportes** personalizados por empresa