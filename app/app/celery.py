"""
Configuración de Celery para el proyecto
"""

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Establecer el módulo de configuración de Django para Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

app = Celery("distribuidora_lucas")

# Usar la configuración de Django
app.config_from_object("django.conf:settings", namespace="CELERY")

# Descubrir tareas automáticamente en todas las aplicaciones
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
