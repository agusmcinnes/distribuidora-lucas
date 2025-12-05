"""
Tareas de Celery para el bot de Telegram
"""

from celery import shared_task
import logging
from .services import TelegramNotificationService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_alert_task(self, alert_type, alert_data):
    """
    Tarea genérica para enviar alertas de forma asíncrona

    Args:
        alert_type: Tipo de alerta (powerbi, system, etc.)
        alert_data: Diccionario con los datos de la alerta
    """
    try:
        service = TelegramNotificationService()

        if alert_type == "powerbi":
            success = service.send_powerbi_alert(alert_data)
        else:
            success = service.send_system_alert(
                alert_data.get("subject", "Alerta del sistema"),
                alert_data.get("message", "")
            )

        if success:
            logger.info(f"Alerta {alert_type} enviada exitosamente")
        else:
            logger.error(f"Error enviando alerta {alert_type}")

        return success

    except Exception as e:
        logger.error(f"Error en tarea de alerta {alert_type}: {e}")

        # Reintentar en caso de error
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)

        return False
