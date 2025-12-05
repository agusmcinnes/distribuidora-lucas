# Integración Power BI - Resumen de Cambios

## Archivos Creados

```
app/powerbi_handler/
├── __init__.py
├── apps.py
├── models.py              # PowerBIConfig, PowerBIAlert, PowerBIProcessingLog
├── services.py            # Autenticación MSAL y queries DAX
├── tasks.py               # Tarea Celery periódica
├── admin.py               # Panel de administración
├── migrations/
│   └── 0001_initial.py
└── management/commands/
    ├── test_powerbi_connection.py
    └── process_powerbi_alerts.py
```

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `requirements.txt` | Agregado `msal>=1.24.0` |
| `app/app/settings.py` | Agregado `powerbi_handler` a SHARED_APPS, variables POWERBI_*, tarea en CELERY_BEAT_SCHEDULE |
| `.env` | Agregadas credenciales de Power BI |

## Credenciales Configuradas (.env)

```
POWERBI_TENANT_ID=your-tenant-id
POWERBI_CLIENT_ID=your-client-id
POWERBI_CLIENT_SECRET=your-client-secret
POWERBI_GROUP_ID=your-group-id
POWERBI_DATASET_ID=your-dataset-id
POWERBI_CHECK_INTERVAL=300
```

## Estado Actual

- **Autenticación**: Funciona correctamente
- **Acceso al workspace**: ERROR - El Service Principal no tiene permisos

## Próximos Pasos

### 1. Dar permisos al Service Principal en Power BI

1. Ir a **app.powerbi.com**
2. Navegar al workspace donde está el dataset
3. Click en **Configuración** → **Administrar acceso**
4. Agregar la aplicación: `your-client-id`
5. Asignar rol: **Miembro** o **Colaborador**

### 2. Verificar el Workspace ID

Confirmar que el POWERBI_GROUP_ID es correcto mirando la URL del workspace en Power BI.

### 3. Probar conexión

```bash
docker-compose exec web python manage.py test_powerbi_connection
```

### 4. Configurar la Query DAX

Desde el admin (`/admin/powerbi_handler/powerbiconfig/`), editar la configuración y agregar:

- **Query DAX**: La query que obtiene los datos/alertas
- **Mapeo de campos**: JSON que mapea columnas del dataset

Ejemplo de mapeo:
```json
{
  "record_id": "ID",
  "company_identifier": "Empresa",
  "subject": "Descripcion",
  "body": "Detalle",
  "priority": "Prioridad",
  "date": "FechaCreacion"
}
```

### 5. Probar procesamiento

```bash
# Modo simulación (no crea alertas)
docker-compose exec web python manage.py process_powerbi_alerts --dry-run

# Ejecución real
docker-compose exec web python manage.py process_powerbi_alerts
```

## Comandos Útiles

```bash
# Probar conexión
docker-compose exec web python manage.py test_powerbi_connection

# Procesar alertas manualmente
docker-compose exec web python manage.py process_powerbi_alerts

# Ver logs de celery
docker-compose logs -f celery

# Reiniciar servicios
docker-compose restart celery celery-beat
```

## Notas

- La tarea `process_powerbi_alerts_task` se ejecuta cada 5 minutos (300 segundos)
- Las alertas se envían a los chats de Telegram configurados con `email_alerts=True`
- Los registros procesados se trackean por `powerbi_record_id` para evitar duplicados
- IMAP sigue funcionando en paralelo
