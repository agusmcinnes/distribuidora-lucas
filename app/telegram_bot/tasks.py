"""
Tareas de Celery para el bot de Telegram
"""

from celery import shared_task
import logging
from .services import TelegramNotificationService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_email_alert_task(self, email_id):
    """
    Tarea para enviar alerta de email de forma asíncrona
    """
    try:
        from emails.models import ReceivedEmail

        # Obtener el email
        email = ReceivedEmail.objects.get(id=email_id)

        # Enviar alerta
        service = TelegramNotificationService()
        success = service.send_email_alert(email)

        if success:
            logger.info(f"Alerta enviada exitosamente para email {email_id}")
        else:
            logger.error(f"Error enviando alerta para email {email_id}")

        return success

    except Exception as e:
        logger.error(f"Error en tarea de alerta de email {email_id}: {e}")

        # Reintentar en caso de error
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)

        return False
