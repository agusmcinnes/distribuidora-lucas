# Guía para Crear Empresas con Django Tenants

## Resumen

Ahora puedes crear empresas completas con tenant, dominio y usuario administrador desde el panel de administración o la línea de comandos. Cada empresa creada tendrá:

- ✅ **Esquema de base de datos independiente** 
- ✅ **Dominio de acceso personalizado**
- ✅ **Usuario administrador con acceso completo**
- ✅ **Roles básicos preconfigurados** (Manager, Supervisor, Client)
- ✅ **Sistema de alertas listo para usar**

## Métodos de Creación

### 1. Desde el Panel de Administración (Recomendado)

#### Pasos:
1. **Accede al super admin**: `http://localhost/admin/` (esquema público)
2. **Ve a "Crear Nueva Empresa"** desde las acciones rápidas en el dashboard
3. **Completa el formulario**:
   - **Nombre de la empresa**: Ej: "Distribuidora Norte S.A."
   - **Schema name**: Ej: "distribuidora_norte" (se auto-genera del nombre)
   - **Dominio**: Ej: "norte.localhost"
   - **Usuario administrador**: Ej: "admin_norte"
   - **Email del admin**: Ej: "admin@norte.com"
   - **Contraseña**: Mínimo 8 caracteres
4. **Haz clic en "🚀 Crear Empresa Completa"**

#### Resultado:
- La empresa se crea automáticamente con todos los componentes
- Recibes un mensaje de confirmación con los datos de acceso
- El dominio aparece como enlace directo al admin de la empresa

### 2. Desde la Línea de Comandos

```bash
# Comando básico
python manage.py create_company "Distribuidora Sur" "distribuidora_sur" "sur.localhost" "admin_sur" "admin@sur.com"

# Con contraseña específica
python manage.py create_company "Distribuidora Este" "distribuidora_este" "este.localhost" "admin_este" "admin@este.com" --admin-password "MiPassword123"

# Crear empresa inactiva
python manage.py create_company "Distribuidora Oeste" "distribuidora_oeste" "oeste.localhost" "admin_oeste" "admin@oeste.com" --inactive
```

#### Parámetros:
- `company_name`: Nombre descriptivo de la empresa
- `schema_name`: Nombre del esquema PostgreSQL (solo letras, números, guiones y guiones bajos)
- `domain`: Dominio para acceder (ej: empresa.localhost)
- `admin_username`: Usuario administrador
- `admin_email`: Email del administrador
- `--admin-password`: Contraseña específica (opcional, se pide interactivamente si no se proporciona)
- `--inactive`: Crear la empresa como inactiva

## Configuración de Dominios

### Para Desarrollo Local:

#### Opción 1: Usar subdominios con .localhost
```
norte.localhost
sur.localhost  
este.localhost
oeste.localhost
```

#### Opción 2: Configurar hosts locales
Edita el archivo hosts (`C:\Windows\System32\drivers\etc\hosts` en Windows):
```
127.0.0.1 empresa1.local
127.0.0.1 empresa2.local
127.0.0.1 empresa3.local
```

### Para Producción:
```
empresa1.tudominio.com
empresa2.tudominio.com
empresa3.tudominio.com
```

## Estructura Creada Automáticamente

### 1. En el Esquema Público (`public`):
```sql
-- Tabla: company_company
INSERT INTO company_company (name, schema_name, is_active, created_at, updated_at)
VALUES ('Distribuidora Norte S.A.', 'distribuidora_norte', true, NOW(), NOW());

-- Tabla: company_domain  
INSERT INTO company_domain (domain, tenant_id, is_primary)
VALUES ('norte.localhost', <company_id>, true);
```

### 2. En el Esquema del Tenant (`distribuidora_norte`):
```sql
-- Usuario Django Auth
INSERT INTO auth_user (username, email, password, is_staff, is_superuser, is_active)
VALUES ('admin_norte', 'admin@norte.com', '<hashed_password>', true, true, true);

-- Roles del sistema
INSERT INTO user_role (type, description) VALUES 
('manager', 'Rol de administrador con acceso completo'),
('supervisor', 'Rol de supervisor con acceso limitado'),
('client', 'Rol de cliente básico');

-- Usuario del sistema personalizado
INSERT INTO user_user (name, email, role_id, company_id, is_active, can_receive_alerts)
VALUES ('Administrador Distribuidora Norte S.A.', 'admin@norte.com', <manager_role_id>, <company_id>, true, true);
```

## Acceso a las Empresas

### URLs de Acceso:
- **Super Admin**: `http://localhost/admin/` (gestión global)
- **Empresa Norte**: `http://norte.localhost/admin/` (solo datos de Norte)
- **Empresa Sur**: `http://sur.localhost/admin/` (solo datos de Sur)

### Credenciales por Empresa:
Cada empresa tiene sus propias credenciales de acceso que defines al crearla.

## Funcionalidades del Admin

### Super Admin (Esquema Público):
- ✅ **Dashboard con estadísticas** de todas las empresas
- ✅ **Crear nuevas empresas** con el formulario mejorado
- ✅ **Ver datos cross-tenant** de todas las empresas
- ✅ **Gestionar dominios** y configuración global
- ✅ **Accesos directos** a cada empresa

### Admin por Empresa (Esquema Tenant):
- ✅ **Admin personalizado** con el nombre de la empresa
- ✅ **Gestión de usuarios** específicos de la empresa
- ✅ **Procesamiento de emails** de la empresa
- ✅ **Configuración de Telegram** específica
- ✅ **Sistema de alertas** personalizado

## Validaciones Implementadas

### En el Formulario:
- ✅ **Schema name único** - no se puede repetir
- ✅ **Dominio único** - cada empresa tiene su dominio exclusivo
- ✅ **Contraseñas coincidentes** - validación en tiempo real
- ✅ **Formato de schema** - solo caracteres válidos
- ✅ **Longitud mínima** de contraseña (8 caracteres)

### En el Command:
- ✅ **Parámetros requeridos** - todos los campos obligatorios
- ✅ **Validación de duplicados** - schema y dominio únicos
- ✅ **Confirmación de contraseña** - input interactivo seguro
- ✅ **Rollback automático** - si hay error, no se crea nada

## Troubleshooting

### Error: "Ya existe una empresa con el schema"
**Solución**: Usa un schema_name diferente. Los schemas deben ser únicos.

### Error: "Ya existe el dominio"
**Solución**: Usa un dominio diferente. Cada empresa necesita su propio dominio.

### Error: "No tenant for hostname"
**Causa**: El dominio no está configurado correctamente.
**Solución**: 
1. Verifica que el dominio esté en la tabla `company_domain`
2. Verifica que `is_primary=True`
3. Verifica la configuración de hosts o DNS

### Error: "relation does not exist"
**Causa**: Las migraciones no se han ejecutado en el tenant.
**Solución**:
```bash
python manage.py migrate_schemas --tenant
```

### No aparecen los datos del tenant
**Causa**: Estás en el esquema incorrecto.
**Solución**: Verifica que estés accediendo desde el dominio correcto de la empresa.

## Comandos Útiles

### Ver todas las empresas:
```bash
python manage.py shell
>>> from company.models import Company
>>> Company.objects.all()
```

### Migrar un tenant específico:
```bash
python manage.py migrate_schemas --schema=distribuidora_norte
```

### Migrar todos los tenants:
```bash
python manage.py migrate_schemas --tenant
```

### Crear superusuario en un tenant:
```bash
python manage.py tenant_command createsuperuser --schema=distribuidora_norte
```

## Próximos Pasos

1. **Configurar emails IMAP** por empresa
2. **Configurar bots de Telegram** por empresa  
3. **Personalizar templates** por empresa
4. **Configurar dominios de producción**
5. **Implementar backups** por tenant

## Estructura de Archivos Modificados

```
app/
├── company/
│   ├── admin.py                 # ✨ Formulario personalizado para crear empresas
│   ├── management/
│   │   └── commands/
│   │       └── create_company.py # ✨ Command para crear empresas
│   └── views.py                 # ✨ Vista de admin personalizada
├── templates/
│   └── admin/
│       ├── index.html           # ✨ Dashboard mejorado con estadísticas
│       └── company/company/
│           └── add_form.html    # ✨ Template para crear empresas
└── app/
    └── urls_public.py           # ✨ URLs del esquema público actualizadas
```

## Notas Importantes

- ⚠️ **No modifiques** el `schema_name` después de crear la empresa
- ⚠️ **No elimines** empresas sin hacer backup de sus datos
- ⚠️ **Usa HTTPS** en producción para las credenciales
- ✅ **Cada empresa** tiene sus datos completamente aislados
- ✅ **El sistema** es escalable a miles de empresas