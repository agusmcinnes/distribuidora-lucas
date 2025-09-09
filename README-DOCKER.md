# Distribuidora Lucas - Configuración Docker

Este documento explica cómo poner en funcionamiento el sistema de procesamiento de emails con Docker.

## Prerequisitos

- Docker y Docker Compose instalados
- Archivo `.env` configurado con tus credenciales

## Arquitectura del Sistema

El sistema está compuesto por 5 servicios Docker:

1. **PostgreSQL** (`db`): Base de datos principal
2. **Redis** (`redis`): Broker para Celery
3. **Django Web** (`web`): Aplicación web principal
4. **Celery Worker** (`celery`): Procesador de tareas asíncronas
5. **Celery Beat** (`celery-beat`): Scheduler para tareas periódicas

## Configuración Inicial

### 1. Configurar Variables de Entorno

Edita el archivo `.env` y configura las siguientes variables:

```bash
# IMAP Configuration
IMAP_EMAIL=tu-email@gmail.com
IMAP_PASSWORD=tu-app-password

# Telegram Configuration
TELEGRAM_BOT_TOKEN=tu-bot-token
TELEGRAM_CHAT_ID=tu-chat-id
```

### 2. Iniciar los Servicios

```bash
# Construir e iniciar todos los servicios
docker-compose up --build

# O para ejecutar en segundo plano
docker-compose up -d --build
```

### 3. Ejecutar Migraciones

En otra terminal, ejecuta:

```bash
# Crear y aplicar migraciones
docker-compose exec web python app/manage.py makemigrations
docker-compose exec web python app/manage.py migrate

# Crear superusuario (opcional)
docker-compose exec web python app/manage.py createsuperuser
```

## Comandos Útiles

### Gestión de Servicios

```bash
# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f web
docker-compose logs -f celery
docker-compose logs -f celery-beat

# Parar todos los servicios
docker-compose stop

# Reiniciar un servicio específico
docker-compose restart web

# Eliminar todos los contenedores y volúmenes
docker-compose down -v
```

### Django Management

```bash
# Ejecutar comandos de Django
docker-compose exec web python app/manage.py shell
docker-compose exec web python app/manage.py collectstatic

# Acceder al contenedor web
docker-compose exec web bash
```

### Celery Monitoring

```bash
# Ver workers activos
docker-compose exec celery celery -A app.celery inspect active

# Ver tareas programadas
docker-compose exec celery-beat celery -A app.celery inspect scheduled
```

## Funcionamiento del Sistema

1. **Celery Beat** ejecuta la tarea `process_imap_emails_task` cada minuto
2. **Celery Worker** procesa los emails recibidos
3. Los emails procesados se envían a **Telegram**
4. Todo se almacena en **PostgreSQL**

## Puertos Expuestos

- **8000**: Django Web App
- **5432**: PostgreSQL
- **6379**: Redis

## Acceso a la Aplicación

- Web App: http://localhost:8000
- Admin Panel: http://localhost:8000/admin

## Troubleshooting

### Error de Conexión a PostgreSQL

Si ves errores de conexión, asegúrate de que el servicio `db` esté corriendo:

```bash
docker-compose ps
docker-compose logs db
```

### Celery no procesa tareas

Verifica que Redis esté funcionando:

```bash
docker-compose logs redis
docker-compose exec redis redis-cli ping
```

### Problema con migraciones

Borra la base de datos y empieza desde cero:

```bash
docker-compose down -v
docker-compose up -d db
docker-compose exec web python app/manage.py migrate
```

## Estructura de Archivos Docker

```
.
├── Dockerfile              # Imagen de la aplicación
├── docker-compose.yml      # Orquestación de servicios
├── .dockerignore           # Archivos a ignorar en build
├── .env                    # Variables de entorno
└── README-DOCKER.md        # Esta documentación
```

## Monitoreo

Para verificar que todo funciona correctamente:

1. Revisa los logs: `docker-compose logs -f`
2. Accede a la web app: http://localhost:8000
3. Verifica que Celery esté procesando: `docker-compose logs celery`
4. Comprueba que lleguen emails de prueba

¡El sistema debería estar funcionando y procesando emails automáticamente!