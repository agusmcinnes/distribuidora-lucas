"""
Configuración de la aplicación Django para Power BI Handler
"""

from django.apps import AppConfig


class PowerbiHandlerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "powerbi_handler"
    verbose_name = "Power BI Handler"
