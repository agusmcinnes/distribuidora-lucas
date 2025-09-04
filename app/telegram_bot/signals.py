"""
Señales de Django para el bot de Telegram
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from emails.models import ReceivedEmail
from .services import TelegramNotificationService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ReceivedEmail)
def send_telegram_alert_on_new_email(sender, instance, created, **kwargs):
    """
    Enviar alerta de Telegram cuando se crea un nuevo email
    """
    if created:  # Solo para emails nuevos
        try:
            logger.info(
                f"Nuevo email recibido de {instance.sender}: {instance.subject}"
            )

            # Enviar alerta inmediatamente (sin Celery para simplicidad)
            service = TelegramNotificationService()
            success = service.send_email_alert(instance)

            if success:
                logger.info(
                    f"Alerta de Telegram enviada para email: {instance.subject}"
                )
            else:
                logger.warning(f"Error enviando alerta para email: {instance.subject}")

        except Exception as e:
            logger.error(f"Error en señal de Telegram: {e}")
