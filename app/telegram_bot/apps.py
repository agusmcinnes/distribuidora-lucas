"""
Configuración de la aplicación Django para el bot de Telegram
"""

from django.apps import AppConfig


class TelegramBotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "telegram_bot"
    verbose_name = "Bot de Telegram"

    def ready(self):
        """
        Código que se ejecuta cuando la aplicación está lista.
        Aquí se pueden registrar señales y configurar webhooks.
        """
        # Importar señales para que se registren
        try:
            from . import signals
        except ImportError:
            pass
