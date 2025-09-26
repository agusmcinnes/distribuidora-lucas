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
    Tarea programada para procesar emails IMAP de manera asíncrona para todos los tenants
    """
    try:
        # Importar aquí para evitar circular imports
        from .services import IMAPService
        from .models import IMAPConfiguration
        from company.models import Company
        from django_tenants.utils import tenant_context

        logger.info(
            f"🚀 Iniciando procesamiento IMAP programado - Task ID: {self.request.id}"
        )

        service = IMAPService()
        total_processed = 0
        total_failed = 0
        results_by_company = {}

        # Procesar emails para todas las empresas activas
        companies = Company.objects.filter(is_active=True).exclude(schema_name='public')
        
        for company in companies:
            try:
                with tenant_context(company):
                    logger.info(f"📧 Procesando emails para {company.name}")
                    
                    # Obtener o crear configuración IMAP para este tenant
                    config, created = IMAPConfiguration.objects.get_or_create(
                        name="Gmail Configuration",
                        defaults={
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

                    # Actualizar configuración con valores del .env
                    if not created:
                        config.host = settings.IMAP_HOST
                        config.port = settings.IMAP_PORT
                        config.username = settings.IMAP_EMAIL
                        config.password = settings.IMAP_PASSWORD
                        config.use_ssl = settings.IMAP_USE_SSL
                        config.inbox_folder = settings.IMAP_FOLDER_INBOX
                        config.processed_folder = settings.IMAP_FOLDER_PROCESSED
                        config.max_emails_per_check = settings.IMAP_BATCH_SIZE
                        config.save()

                    # Procesar emails para este tenant
                    result = service.process_emails_for_config(config)
                    
                    company_processed = result.get('processed', 0)
                    company_failed = result.get('failed', 0)
                    
                    total_processed += company_processed
                    total_failed += company_failed
                    
                    results_by_company[company.name] = {
                        'processed': company_processed,
                        'failed': company_failed
                    }
                    
                    logger.info(f"✅ {company.name}: {company_processed} procesados, {company_failed} fallidos")
                    
            except Exception as e:
                logger.error(f"❌ Error procesando emails para {company.name}: {str(e)}")
                results_by_company[company.name] = {'error': str(e)}

        logger.info(
            f"✅ Tarea IMAP completada - Total Procesados: {total_processed}, Total Fallidos: {total_failed}"
        )

        return {
            "status": "success",
            "task_id": self.request.id,
            "timestamp": timezone.now().isoformat(),
            "total_processed": total_processed,
            "total_failed": total_failed,
            "results_by_company": results_by_company,
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
def send_telegram_alert_task(tenant_schema, chat_id, message, priority="medium"):
    """
    Enviar alerta por Telegram para un tenant específico
    """
    try:
        from company.models import Company
        from django_tenants.utils import tenant_context
        
        # Obtener el tenant por su schema
        company = Company.objects.get(schema_name=tenant_schema)
        
        with tenant_context(company):
            from telegram_bot.services import TelegramService
            
            logger.info(
                f"📱 Enviando alerta Telegram a {company.name}, chat {chat_id}: {message[:50]}... (Prioridad: {priority})"
            )
            
            # Usar el servicio de Telegram
            telegram_service = TelegramService()
            result = telegram_service.send_message(chat_id, message, priority)
            
            logger.info(f"✅ Telegram enviado: {result.get('status', 'unknown')}")
            
            return {
                "status": "success",
                "company": company.name,
                "chat_id": chat_id,
                "message": message[:100] + "..." if len(message) > 100 else message,
                "priority": priority,
                "timestamp": timezone.now().isoformat(),
                "telegram_result": result
            }

    except Company.DoesNotExist:
        error_msg = f"Tenant {tenant_schema} no encontrado"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}
    except Exception as e:
        logger.error(f"❌ Error en alerta Telegram: {str(e)}")
        return {"status": "error", "message": str(e), "tenant_schema": tenant_schema}


@shared_task(name="imap_handler.tasks.cleanup_old_emails_task")
def cleanup_old_emails_task(days_old=30):
    """
    Limpiar emails antiguos para mantener la base de datos eficiente en todos los tenants
    """
    try:
        from emails.models import ReceivedEmail
        from datetime import timedelta
        from company.models import Company
        from django_tenants.utils import tenant_context

        cutoff_date = timezone.now() - timedelta(days=days_old)
        total_deleted = 0
        results_by_company = {}

        # Limpiar emails en todos los tenants
        companies = Company.objects.filter(is_active=True).exclude(schema_name='public')
        
        for company in companies:
            try:
                with tenant_context(company):
                    old_emails = ReceivedEmail.objects.filter(received_date__lt=cutoff_date)
                    count = old_emails.count()
                    
                    if count > 0:
                        old_emails.delete()
                        logger.info(
                            f"🧹 {company.name}: {count} emails eliminados (más de {days_old} días)"
                        )
                    else:
                        logger.info(
                            f"🧹 {company.name}: No hay emails antiguos para limpiar"
                        )
                    
                    total_deleted += count
                    results_by_company[company.name] = count
                    
            except Exception as e:
                logger.error(f"❌ Error limpiando {company.name}: {str(e)}")
                results_by_company[company.name] = f"Error: {str(e)}"

        logger.info(
            f"🧹 Limpieza completada: {total_deleted} emails eliminados total (más de {days_old} días)"
        )

        return {
            "status": "success",
            "total_emails_deleted": total_deleted,
            "results_by_company": results_by_company,
            "days_old": days_old,
            "timestamp": timezone.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Error en limpieza: {str(e)}")
        return {"status": "error", "message": str(e)}
