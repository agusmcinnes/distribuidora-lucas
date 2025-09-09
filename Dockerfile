# Dockerfile para la aplicación Django
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /code/app

# Copiar requirements.txt
COPY requirements.txt /code/

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r /code/requirements.txt

# Copiar código de la aplicación
COPY . /code

# Crear directorio para logs
RUN mkdir -p /code/app/logs

# Establecer permisos
RUN chmod +x /code/app/manage.py

# Exponer puerto
EXPOSE 8000

# Comando por defecto para Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]