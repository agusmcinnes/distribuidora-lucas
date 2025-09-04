"""
Tareas de Celery para procesamiento IMAP y alertas
"""

from celery import shared_task, current_task
from django.conf import settings
from django.utils import timezone
import logging
import time

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="imap_handler.tasks.process_imap_emails_task")
def process_imap_emails_task(self):
    """
    Tarea programada para procesar emails IMAP de manera asíncrona
    """
    try:
        # Importar aquí para evitar circular imports
        from .services import IMAPService
        from .models import IMAPConfiguration
        from company.models import Company

        logger.info(
            f"🚀 Iniciando procesamiento IMAP programado - Task ID: {self.request.id}"
        )

        # Crear o actualizar configuración basada en variables de entorno
        company, _ = Company.objects.get_or_create(
            name="Distribuidora Lucas", defaults={"is_active": True}
        )

        config, created = IMAPConfiguration.objects.get_or_create(
            name="Gmail Distribuidora",
            defaults={
                "company": company,
                "host": settings.IMAP_HOST,
                "port": settings.IMAP_PORT,
                "username": settings.IMAP_EMAIL,
                "password": settings.IMAP_PASSWORD,
                "use_ssl": settings.IMAP_USE_SSL,
                "inbox_folder": settings.IMAP_FOLDER_INBOX,
                "processed_folder": settings.IMAP_FOLDER_PROCESSED,
                "is_active": True,
                "max_emails_per_check": settings.IMAP_BATCH_SIZE,
            },
        )

        # Si no es nueva, actualizar con valores del .env
        if not created:
            config.company = company
            config.host = settings.IMAP_HOST
            config.port = settings.IMAP_PORT
            config.username = settings.IMAP_EMAIL
            config.password = settings.IMAP_PASSWORD
            config.use_ssl = settings.IMAP_USE_SSL
            config.inbox_folder = settings.IMAP_FOLDER_INBOX
            config.processed_folder = settings.IMAP_FOLDER_PROCESSED
            config.max_emails_per_check = settings.IMAP_BATCH_SIZE
            config.save()

        # Procesar emails
        service = IMAPService()
        result = service.process_emails_for_config(config)

        logger.info(
            f"✅ Tarea IMAP completada - Procesados: {result.get('processed', 0)}, Fallidos: {result.get('failed', 0)}"
        )

        return {
            "status": "success",
            "task_id": self.request.id,
            "timestamp": timezone.now().isoformat(),
            "config_name": config.name,
            "result": result,
        }

    except Exception as e:
        logger.error(f"❌ Error en tarea IMAP: {str(e)}", exc_info=True)

        # Retry después de 60 segundos, máximo 3 intentos
        raise self.retry(countdown=60, max_retries=3, exc=e)


@shared_task(bind=True, name="imap_handler.tasks.process_single_account_task")
def process_single_account_task(self, config_id):
    """
    Procesar una cuenta IMAP específica de manera asíncrona
    """
    try:
        from .services import IMAPService
        from .models import IMAPConfiguration

        logger.info(
            f"🔄 Procesando cuenta específica ID: {config_id} - Task: {self.request.id}"
        )

        config = IMAPConfiguration.objects.get(id=config_id, is_active=True)
        service = IMAPService()
        result = service.process_emails_for_config(config)

        logger.info(f"✅ Procesamiento completado para {config.name}")

        return {
            "status": "success",
            "config_id": config_id,
            "config_name": config.name,
            "result": result,
            "task_id": self.request.id,
        }

    except IMAPConfiguration.DoesNotExist:
        error_msg = f"Configuración IMAP {config_id} no encontrada o inactiva"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg, "task_id": self.request.id}
    except Exception as e:
        logger.error(f"❌ Error procesando cuenta {config_id}: {str(e)}", exc_info=True)
        raise self.retry(countdown=30, max_retries=2, exc=e)


@shared_task(bind=True, name="imap_handler.tasks.test_imap_connection_task")
def test_imap_connection_task(self, config_id=None):
    """
    Probar conexión IMAP de manera asíncrona
    """
    try:
        from .services import IMAPService
        from .models import IMAPConfiguration

        service = IMAPService()

        if config_id:
            # Probar configuración específica
            config = IMAPConfiguration.objects.get(id=config_id)
            result = service.test_connection_for_config(config)
            logger.info(
                f"🔍 Test conexión para {config.name}: {result.get('status', 'unknown')}"
            )
        else:
            # Probar configuración desde variables de entorno
            result = service.test_connection_from_env()
            logger.info(
                f"🔍 Test conexión desde .env: {result.get('status', 'unknown')}"
            )

        return {
            "status": result.get("status", "unknown"),
            "message": result.get("message", ""),
            "details": result.get("details", {}),
            "task_id": self.request.id,
            "timestamp": timezone.now().isoformat(),
        }

    except IMAPConfiguration.DoesNotExist:
        error_msg = f"Configuración IMAP {config_id} no encontrada"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg, "task_id": self.request.id}
    except Exception as e:
        logger.error(f"❌ Error probando conexión: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e), "task_id": self.request.id}


@shared_task(name="imap_handler.tasks.send_telegram_alert_task")
def send_telegram_alert_task(user_id, message, priority="medium"):
    """
    Enviar alerta por Telegram (preparado para implementación futura)
    """
    try:
        # Aquí irá la lógica de Telegram cuando se implemente
        logger.info(
            f"📱 Alerta Telegram preparada para usuario {user_id}: {message} (Prioridad: {priority})"
        )

        # Por ahora solo logueamos, más adelante se implementará el bot
        return {
            "status": "success",
            "user_id": user_id,
            "message": message[:100] + "..." if len(message) > 100 else message,
            "priority": priority,
            "timestamp": timezone.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Error en alerta Telegram: {str(e)}")
        return {"status": "error", "message": str(e), "user_id": user_id}


@shared_task(name="imap_handler.tasks.cleanup_old_emails_task")
def cleanup_old_emails_task(days_old=30):
    """
    Limpiar emails antiguos para mantener la base de datos eficiente
    """
    try:
        from emails.models import ReceivedEmail
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=days_old)
        old_emails = ReceivedEmail.objects.filter(received_date__lt=cutoff_date)
        count = old_emails.count()

        if count > 0:
            old_emails.delete()
            logger.info(
                f"🧹 Limpieza completada: {count} emails eliminados (más de {days_old} días)"
            )
        else:
            logger.info(
                f"🧹 No hay emails antiguos para limpiar (más de {days_old} días)"
            )

        return {
            "status": "success",
            "emails_deleted": count,
            "days_old": days_old,
            "timestamp": timezone.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Error en limpieza: {str(e)}")
        return {"status": "error", "message": str(e)}
