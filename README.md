# 🚀 DISTRIBUIDORA LUCAS - SISTEMA DE ALERTAS

Sistema automático de alertas que recibe emails de Gmail y los registra en tiempo real.

## ⚡ INSTALACIÓN RÁPIDA

### 1. Clonar repositorio:
```bash
git clone https://github.com/agusmcinnes/distribuidora-lucas.git
cd distribuidora-lucas
```

### 2. Configurar entorno Python:
```bash
# Crear entorno virtual
python -m venv .envs/lucas

# Activar entorno (Windows)
.envs/lucas/Scripts/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar Gmail:
- Ir a: https://myaccount.google.com/security
- Activar verificación en 2 pasos
- Crear "Contraseña de aplicación" para Gmail

### 4. Configurar variables de entorno:
```bash
# Copiar archivo de ejemplo
copy .env.example .env

# Editar .env con tus credenciales:
IMAP_EMAIL=tu-email@gmail.com
IMAP_PASSWORD=tu-app-password-de-16-caracteres
```

### 5. Configurar base de datos:
```bash
cd app
python manage.py migrate
python manage.py createsuperuser
```

### 6. Iniciar sistema:
```bash
# Opción 1: Script automático (Windows)
start_auto_emails.bat

# Opción 2: Comando manual
python manage.py auto_process --interval 60
```

## 📊 Panel Administrativo:
- URL: http://127.0.0.1:8000/admin/
- Ver emails recibidos en: **EMAILS > Received emails**

## 📧 FUNCIÓN PRINCIPAL:
El sistema recibe automáticamente TODOS los emails de Gmail y los registra en la base de datos cada 60 segundos con clasificación de prioridad automática.

## 🧪 COMANDOS DE PRUEBA:
```bash
# Probar conexión IMAP
python manage.py test_imap_connection

# Procesar emails manualmente (una vez)
python manage.py process_imap_emails

# Procesamiento automático continuo
python manage.py auto_process --interval 60
```

## 📖 Documentación Completa:
- **Para Gerencia:** `RESUMEN_EJECUTIVO.md`
- **Técnica Completa:** `DOCUMENTACION_TECNICA.md`
- **Lista de Archivos:** `ARCHIVOS_DEL_SISTEMA.md`

## 🔐 Seguridad:
- Las credenciales están en `.env` (no se sube a Git)
- Conexión SSL segura a Gmail
- App Password (no contraseña real)

## 📋 Estructura del Proyecto:
```
distribuidora-lucas/
├── 📄 .env.example              # Plantilla de configuración
├── 📄 requirements.txt          # Dependencias Python
├── 📄 start_auto_emails.bat     # Script de inicio (Windows)
├── 📁 app/                      # Aplicación Django principal
│   ├── manage.py                # Comandos Django
│   ├── 📁 emails/               # App de emails (principal)
│   ├── 📁 imap_handler/         # Procesamiento IMAP
│   ├── 📁 company/              # Gestión empresas
│   └── 📁 user/                 # Gestión usuarios
└── 📁 .envs/                    # Entorno virtual (no en Git)
```

## 🚀 Estado:
✅ **SISTEMA COMPLETAMENTE FUNCIONAL**  
✅ **LISTO PARA PRODUCCIÓN**  
✅ **DOCUMENTACIÓN COMPLETA**