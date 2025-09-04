# 📋 LISTA DE ARCHIVOS DEL SISTEMA

## ✅ **ARCHIVOS ESENCIALES (NO ELIMINAR)**

### 📁 **Configuración Principal:**

```
.env                           # Credenciales Gmail (CRÍTICO)
start_auto_emails.bat         # Script de inicio rápido
README.md                     # Guía de instalación
DOCUMENTACION_TECNICA.md      # Documentación completa
```

### 📁 **Aplicación Django (app/):**

```
manage.py                     # Comando principal Django
db.sqlite3                    # Base de datos
```

### 📁 **Configuración Django (app/app/):**

```
settings.py                   # Configuración del sistema
urls.py                       # URLs del sistema
__init__.py, asgi.py, wsgi.py # Archivos estándar Django
```

### 📁 **Aplicaciones Django:**

```
app/company/                  # Gestión de empresas
├── models.py                 # Modelo Company
├── admin.py                  # Admin empresas
└── migrations/               # Migraciones DB

app/user/                     # Gestión de usuarios
├── models.py                 # Modelos Role, User
├── admin.py                  # Admin usuarios
└── migrations/               # Migraciones DB

app/emails/                   # Gestión de emails ⭐ PRINCIPAL
├── models.py                 # Modelo ReceivedEmail
├── admin.py                  # Admin emails
└── migrations/               # Migraciones DB

app/imap_handler/            # Procesamiento IMAP ⭐ PRINCIPAL
├── models.py                # Configuración IMAP
├── services.py              # Lógica de procesamiento
├── admin.py                 # Admin IMAP
├── tasks.py                 # Tareas Celery (backup)
├── management/commands/
│   ├── auto_process.py      # Comando principal ⭐
│   ├── test_imap_connection.py
│   └── process_imap_emails.py
└── migrations/              # Migraciones DB
```

### 📁 **Logs:**

```
app/logs/imap_handler.log    # Archivo de logs
```

---

## ❌ **ARCHIVOS ELIMINADOS (Ya no necesarios)**

```
❌ CLAUDE.md                 # Documentación temporal
❌ README.md (anterior)      # README anterior
❌ IMAP_GUIDE.md            # Guía IMAP antigua
❌ start_worker.bat         # Script Celery worker
❌ start_beat.bat           # Script Celery beat
❌ process_emails.bat       # Script procesamiento antiguo
❌ app/run_imap_processing.bat # Script IMAP antiguo
❌ app/templates/           # Templates innecesarios
❌ app/app/celery.py        # Configuración Celery
❌ app/app/admin_site.py    # Admin personalizado
❌ commands/celery_manager.py # Comando Celery
❌ commands/process_imap.py  # Comando antiguo
```

---

## 🏗️ **ESTRUCTURA FINAL LIMPIA:**

```
distribuidora-lucas/
├── 📄 .env                          # Variables de entorno
├── 📄 README.md                     # Guía rápida
├── 📄 DOCUMENTACION_TECNICA.md      # Documentación completa
├── 📄 ARCHIVOS_DEL_SISTEMA.md       # Este archivo
├── 📄 start_auto_emails.bat         # Script de inicio
│
└── 📁 app/                          # Aplicación Django
    ├── 📄 manage.py                 # Comando Django
    ├── 📄 db.sqlite3               # Base de datos
    │
    ├── 📁 app/                     # Configuración Django
    ├── 📁 company/                 # App empresas
    ├── 📁 user/                    # App usuarios
    ├── 📁 emails/                  # App emails ⭐
    ├── 📁 imap_handler/            # App procesamiento ⭐
    └── 📁 logs/                    # Logs del sistema
```

---

## 🚀 **COMANDOS PRINCIPALES:**

```bash
# Iniciar procesamiento automático
start_auto_emails.bat

# Comando manual con intervalo personalizado
python manage.py auto_process --interval 60

# Probar conexión IMAP
python manage.py test_imap_connection

# Procesar emails manualmente
python manage.py process_imap_emails

# Iniciar servidor web admin
python manage.py runserver
```

---

_Sistema optimizado y limpio - Solo archivos esenciales_
