"""
Tareas Celery para procesamiento de alertas Power BI.
Sistema multi-tenant con soporte para múltiples definiciones de alertas.
"""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="powerbi_handler.tasks.process_all_powerbi_alerts")
def process_all_powerbi_alerts(self):
    """
    Tarea maestra para procesar todas las alertas de Power BI.

    Se ejecuta periódicamente (cada 60 segundos por defecto).
    Verifica cada PowerBIAlertDefinition y procesa las que están pendientes
    según su intervalo configurado.

    Returns:
        Dict con estadísticas del procesamiento
    """
    try:
        from .models import PowerBIGlobalConfig
        from .services import PowerBIAlertService

        logger.info(f"Iniciando procesamiento de Power BI - Task ID: {self.request.id}")

        # Verificar configuración global
        global_config = PowerBIGlobalConfig.objects.filter(is_active=True).first()

        if not global_config:
            logger.warning("No hay configuración global de Power BI activa")
            return {
                "status": "skipped",
                "message": "No hay configuración global activa",
                "task_id": self.request.id,
                "timestamp": timezone.now().isoformat(),
            }

        # Procesar todas las alertas pendientes
        service = PowerBIAlertService(global_config)
        result = service.process_all_pending_alerts()

        logger.info(
            f"Procesamiento completado: "
            f"{result.get('total_definitions_processed', 0)} definiciones, "
            f"{result.get('total_alerts_created', 0)} alertas creadas, "
            f"{result.get('total_alerts_sent', 0)} enviadas"
        )

        return {
            "status": "success",
            "task_id": self.request.id,
            "timestamp": timezone.now().isoformat(),
            "definitions_checked": result.get("total_definitions_checked", 0),
            "definitions_processed": result.get("total_definitions_processed", 0),
            "alerts_created": result.get("total_alerts_created", 0),
            "alerts_sent": result.get("total_alerts_sent", 0),
            "alerts_failed": result.get("total_alerts_failed", 0),
            "by_company": result.get("by_company", {}),
            "errors": result.get("errors", []),
        }

    except Exception as e:
        logger.error(f"Error en tarea de Power BI: {e}", exc_info=True)
        raise self.retry(countdown=60, max_retries=3, exc=e)


@shared_task(bind=True, name="powerbi_handler.tasks.process_single_alert")
def process_single_alert(self, alert_definition_id: int):
    """
    Procesa una única definición de alerta.

    Útil para:
    - Ejecución manual desde admin
    - Testing de alertas específicas
    - Re-procesamiento después de errores

    Args:
        alert_definition_id: ID de la PowerBIAlertDefinition a procesar

    Returns:
        Dict con resultado del procesamiento
    """
    try:
        from .models import PowerBIAlertDefinition, PowerBIGlobalConfig
        from .services import PowerBIAlertService

        logger.info(f"Procesando alerta individual: {alert_definition_id}")

        # Obtener definición
        try:
            definition = PowerBIAlertDefinition.objects.select_related("company").get(
                id=alert_definition_id
            )
        except PowerBIAlertDefinition.DoesNotExist:
            return {
                "status": "error",
                "message": f"Definición de alerta {alert_definition_id} no encontrada",
                "task_id": self.request.id,
            }

        if not definition.is_active:
            return {
                "status": "skipped",
                "message": f"La alerta '{definition.name}' está inactiva",
                "task_id": self.request.id,
            }

        # Obtener configuración global
        global_config = PowerBIGlobalConfig.objects.filter(is_active=True).first()
        if not global_config:
            return {
                "status": "error",
                "message": "No hay configuración global de Power BI activa",
                "task_id": self.request.id,
            }

        # Procesar
        service = PowerBIAlertService(global_config)
        result = service._process_alert_definition(definition)

        logger.info(
            f"Alerta '{definition.name}' procesada: "
            f"{result.get('alerts_created', 0)} creadas, "
            f"{result.get('alerts_sent', 0)} enviadas"
        )

        return {
            "status": "success",
            "task_id": self.request.id,
            "timestamp": timezone.now().isoformat(),
            "alert_definition": definition.name,
            "company": definition.company.name,
            **result,
        }

    except Exception as e:
        logger.error(f"Error procesando alerta {alert_definition_id}: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "task_id": self.request.id,
        }


@shared_task(name="powerbi_handler.tasks.test_powerbi_connection_task")
def test_powerbi_connection_task(
    global_config_id: int = None,
    group_id: str = None,
    dataset_id: str = None,
    dax_query: str = None,
):
    """
    Prueba la conexión a Power BI de forma asíncrona.

    Args:
        global_config_id: ID de la configuración global (opcional)
        group_id: ID del workspace a probar
        dataset_id: ID del dataset a probar
        dax_query: Query DAX a probar (opcional)

    Returns:
        Dict con resultado del test
    """
    try:
        from .models import PowerBIGlobalConfig
        from .services import test_powerbi_connection

        global_config = None
        if global_config_id:
            global_config = PowerBIGlobalConfig.objects.filter(
                id=global_config_id
            ).first()

        result = test_powerbi_connection(
            global_config=global_config,
            group_id=group_id,
            dataset_id=dataset_id,
            dax_query=dax_query,
        )

        status = "exitoso" if result["success"] else "fallido"
        logger.info(f"Test de conexión Power BI: {status}")

        return result

    except Exception as e:
        logger.error(f"Error en test de conexión Power BI: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@shared_task(name="powerbi_handler.tasks.test_openai_connection_task")
def test_openai_connection_task(api_key: str = None):
    """
    Prueba la conexión a OpenAI de forma asíncrona.

    Args:
        api_key: API key de OpenAI (usa settings si no se proporciona)

    Returns:
        Dict con resultado del test
    """
    try:
        from .services import test_openai_connection

        result = test_openai_connection(api_key=api_key)

        status = "exitoso" if result["success"] else "fallido"
        logger.info(f"Test de conexión OpenAI: {status}")

        return result

    except Exception as e:
        logger.error(f"Error en test de conexión OpenAI: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@shared_task(name="powerbi_handler.tasks.cleanup_old_alert_instances")
def cleanup_old_alert_instances(days_old: int = 30):
    """
    Limpia instancias de alertas antiguas.

    Elimina instancias de alertas enviadas que son más antiguas que
    el número de días especificado.

    Args:
        days_old: Número de días después de los cuales las alertas se consideran antiguas

    Returns:
        Dict con estadísticas de limpieza
    """
    try:
        from datetime import timedelta
        from .models import PowerBIAlertInstance

        cutoff_date = timezone.now() - timedelta(days=days_old)

        # Eliminar alertas enviadas más antiguas que el cutoff
        deleted_count, _ = PowerBIAlertInstance.objects.filter(
            status="sent",
            created_at__lt=cutoff_date,
        ).delete()

        logger.info(f"Eliminadas {deleted_count} instancias de alertas antiguas")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "days_old": days_old,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error limpiando alertas antiguas: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@shared_task(name="powerbi_handler.tasks.cleanup_old_processing_logs")
def cleanup_old_processing_logs(days_old: int = 7):
    """
    Limpia logs de procesamiento antiguos.

    Args:
        days_old: Número de días después de los cuales los logs se eliminan

    Returns:
        Dict con estadísticas de limpieza
    """
    try:
        from datetime import timedelta
        from .models import PowerBIProcessingLog

        cutoff_date = timezone.now() - timedelta(days=days_old)

        # Eliminar logs más antiguos que el cutoff
        deleted_count, _ = PowerBIProcessingLog.objects.filter(
            created_at__lt=cutoff_date,
        ).delete()

        logger.info(f"Eliminados {deleted_count} logs de procesamiento antiguos")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "days_old": days_old,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error limpiando logs antiguos: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@shared_task(name="powerbi_handler.tasks.retry_failed_alerts")
def retry_failed_alerts(max_retries: int = 3):
    """
    Reintenta enviar alertas que fallaron.

    Busca instancias de alertas con status='failed' e intenta
    reenviarlas a Telegram.

    Args:
        max_retries: Número máximo de reintentos antes de marcar como ignorada

    Returns:
        Dict con estadísticas de reintento
    """
    try:
        from .models import PowerBIAlertInstance, PowerBIGlobalConfig
        from .services import PowerBIAlertService

        result = {
            "status": "success",
            "total_retried": 0,
            "total_sent": 0,
            "total_failed": 0,
        }

        # Obtener configuración global
        global_config = PowerBIGlobalConfig.objects.filter(is_active=True).first()
        if not global_config:
            return {
                "status": "error",
                "message": "No hay configuración global de Power BI activa",
            }

        service = PowerBIAlertService(global_config)

        # Obtener alertas fallidas
        failed_instances = PowerBIAlertInstance.objects.filter(
            status="failed",
            alert_definition__is_active=True,
        ).select_related("alert_definition", "company")

        for instance in failed_instances:
            result["total_retried"] += 1

            try:
                # Intentar reenviar
                if service._send_to_telegram(instance, instance.alert_definition):
                    result["total_sent"] += 1
                else:
                    result["total_failed"] += 1
            except Exception as e:
                logger.error(f"Error reintentando alerta {instance.id}: {e}")
                result["total_failed"] += 1

        logger.info(
            f"Reintento de alertas: {result['total_retried']} intentadas, "
            f"{result['total_sent']} enviadas, {result['total_failed']} fallidas"
        )

        return result

    except Exception as e:
        logger.error(f"Error en reintento de alertas: {e}")
        return {
            "status": "error",
            "error": str(e),
        }
