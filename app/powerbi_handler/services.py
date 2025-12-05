"""
Servicios para integración con Power BI
Incluye autenticación MSAL, ejecución de queries DAX, formateo con OpenAI
y procesamiento de alertas multi-tenant.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

import msal
import requests
from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from .models import (
    PowerBIGlobalConfig,
    PowerBITenantConfig,
    PowerBIAlertDefinition,
    PowerBIAlertInstance,
    PowerBIProcessingLog,
)

logger = logging.getLogger(__name__)


class PowerBIAuthError(Exception):
    """Error de autenticación con Power BI"""
    pass


class PowerBIQueryError(Exception):
    """Error al ejecutar query DAX"""
    pass


class OpenAIFormatterError(Exception):
    """Error al formatear con OpenAI"""
    pass


# =============================================================================
# OpenAI Formatter Service
# =============================================================================


class OpenAIFormatterService:
    """
    Servicio para formatear datos de Power BI usando OpenAI API.
    Genera mensajes legibles para Telegram a partir de datos crudos.
    """

    OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, "OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("OpenAI API key no configurada")
        self.model = getattr(settings, "OPENAI_MODEL", "gpt-3.5-turbo")
        self.max_tokens = getattr(settings, "OPENAI_MAX_TOKENS", 500)

    def format_alert(
        self,
        raw_data: dict,
        template: str = "",
        example_output: str = "",
        context: dict = None,
    ) -> str:
        """
        Formatea datos crudos de Power BI en un mensaje legible para Telegram.

        Args:
            raw_data: Diccionario con datos del registro de Power BI
            template: Template/instrucciones para OpenAI
            example_output: Ejemplo del formato de salida esperado
            context: Contexto adicional (company_name, alert_name, timestamp)

        Returns:
            Mensaje formateado como string
        """
        context = context or {}

        # Construir el prompt
        system_prompt = self._build_system_prompt(template, example_output)
        user_message = self._build_user_message(raw_data, context)

        try:
            response = requests.post(
                self.OPENAI_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": self.max_tokens,
                    "temperature": 0.3,
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                formatted = data["choices"][0]["message"]["content"].strip()
                logger.debug(f"OpenAI formateó mensaje exitosamente")
                return formatted
            else:
                logger.error(
                    f"OpenAI API error: {response.status_code} - {response.text[:200]}"
                )
                return self._fallback_format(raw_data, context)

        except requests.Timeout:
            logger.error("OpenAI API timeout")
            return self._fallback_format(raw_data, context)
        except Exception as e:
            logger.error(f"Error en OpenAI formatter: {e}")
            return self._fallback_format(raw_data, context)

    def _build_system_prompt(self, template: str, example_output: str) -> str:
        """Construye el system prompt para OpenAI"""
        base_prompt = """Eres un asistente que formatea datos de alertas de Power BI
para mensajes de Telegram. Debes generar mensajes claros, concisos y bien formateados.

Reglas de formato:
- Usa HTML compatible con Telegram: <b>negrita</b>, <i>cursiva</i>, <code>código</code>
- El mensaje debe ser fácil de leer en un dispositivo móvil
- Incluye la información más importante primero
- Usa emojis apropiados para indicar prioridad o tipo de alerta
- Mantén el mensaje conciso (máximo 300 palabras)"""

        if template:
            base_prompt += f"\n\nInstrucciones específicas del cliente:\n{template}"

        if example_output:
            base_prompt += f"\n\nEjemplo del formato esperado:\n{example_output}"

        return base_prompt

    def _build_user_message(self, raw_data: dict, context: dict) -> str:
        """Construye el mensaje del usuario para OpenAI"""
        msg = "Formatea los siguientes datos de Power BI para una alerta de Telegram:\n\n"

        # Datos en formato JSON legible
        msg += f"```json\n{json.dumps(raw_data, ensure_ascii=False, indent=2)}\n```\n"

        # Contexto adicional
        if context:
            msg += "\nContexto adicional:"
            if context.get("company_name"):
                msg += f"\n- Empresa: {context['company_name']}"
            if context.get("alert_name"):
                msg += f"\n- Tipo de alerta: {context['alert_name']}"
            if context.get("priority"):
                msg += f"\n- Prioridad: {context['priority']}"

        return msg

    def _fallback_format(self, raw_data: dict, context: dict) -> str:
        """Formato de respaldo cuando OpenAI no está disponible"""
        lines = []

        # Header con emoji según prioridad
        priority = context.get("priority", "medium")
        emoji = {"critical": "🚨", "high": "🔴", "medium": "🟡", "low": "🟢"}.get(
            priority, "📊"
        )

        alert_name = context.get("alert_name", "Alerta Power BI")
        lines.append(f"{emoji} <b>{alert_name}</b>")
        lines.append("")

        if context.get("company_name"):
            lines.append(f"<b>Empresa:</b> {context['company_name']}")

        # Datos
        for key, value in raw_data.items():
            # Limitar longitud de valores largos
            str_value = str(value)
            if len(str_value) > 100:
                str_value = str_value[:100] + "..."
            lines.append(f"<b>{key}:</b> {str_value}")

        return "\n".join(lines)


# =============================================================================
# Power BI Authentication Service
# =============================================================================


class PowerBIAuthService:
    """
    Servicio de autenticación OAuth2 con Azure AD usando MSAL.
    Maneja cache de tokens para evitar requests innecesarios.
    """

    AUTHORITY_URL = "https://login.microsoftonline.com/{tenant_id}"
    SCOPE = ["https://analysis.windows.net/powerbi/api/.default"]

    def __init__(self, global_config: PowerBIGlobalConfig):
        self.config = global_config
        self.authority = self.AUTHORITY_URL.format(tenant_id=global_config.tenant_id)
        self._access_token = None
        self._token_expires_at = None

    def get_access_token(self) -> str:
        """
        Obtiene token de acceso usando client credentials flow.
        Implementa cache para evitar requests innecesarios.
        """
        # Verificar si hay token válido en cache
        if self._is_token_valid():
            return self._access_token

        try:
            app = msal.ConfidentialClientApplication(
                self.config.client_id,
                authority=self.authority,
                client_credential=self.config.client_secret,
            )

            result = app.acquire_token_for_client(scopes=self.SCOPE)

            if "access_token" in result:
                self._access_token = result["access_token"]
                # Tokens MSAL típicamente duran 1 hora
                expires_in = result.get("expires_in", 3600)
                # Buffer de 5 minutos antes de expiración
                self._token_expires_at = timezone.now().timestamp() + expires_in - 300
                logger.info("Token de Power BI adquirido exitosamente")
                return self._access_token
            else:
                error = result.get("error", "Unknown error")
                error_desc = result.get("error_description", "No description")
                raise PowerBIAuthError(f"Fallo al obtener token: {error} - {error_desc}")

        except PowerBIAuthError:
            raise
        except Exception as e:
            logger.error(f"Error en autenticación Power BI: {e}")
            raise PowerBIAuthError(f"Error de autenticación: {str(e)}")

    def _is_token_valid(self) -> bool:
        """Verifica si el token actual sigue siendo válido"""
        if not self._access_token or not self._token_expires_at:
            return False
        return timezone.now().timestamp() < self._token_expires_at


# =============================================================================
# Power BI Query Service
# =============================================================================


class PowerBIQueryService:
    """
    Servicio para ejecutar queries DAX contra datasets de Power BI.
    Soporta datasets/groups dinámicos por alerta.
    """

    POWERBI_API_URL = "https://api.powerbi.com/v1.0/myorg"

    def __init__(
        self,
        global_config: PowerBIGlobalConfig,
        group_id: str = None,
        dataset_id: str = None,
    ):
        self.global_config = global_config
        self.auth_service = PowerBIAuthService(global_config)
        self.group_id = group_id
        self.dataset_id = dataset_id

    def execute_query(self, query: str) -> List[Dict]:
        """
        Ejecuta una query DAX y retorna los resultados como lista de diccionarios.

        Args:
            query: Query DAX a ejecutar

        Returns:
            Lista de diccionarios con los registros
        """
        if not self.group_id or not self.dataset_id:
            raise ValueError("group_id y dataset_id deben estar especificados")

        try:
            token = self.auth_service.get_access_token()

            url = (
                f"{self.POWERBI_API_URL}/groups/{self.group_id}"
                f"/datasets/{self.dataset_id}/executeQueries"
            )

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            payload = {
                "queries": [{"query": query}],
                "serializerSettings": {"includeNulls": True},
            }

            logger.info(f"Ejecutando query DAX en dataset {self.dataset_id}")
            response = requests.post(url, headers=headers, json=payload, timeout=60)

            if response.status_code == 200:
                data = response.json()
                rows = self._parse_response(data)
                logger.info(f"Query DAX exitosa: {len(rows)} registros obtenidos")
                return rows
            else:
                error_text = response.text[:500] if response.text else "Sin detalles"
                raise PowerBIQueryError(
                    f"Error {response.status_code} al ejecutar query: {error_text}"
                )

        except PowerBIQueryError:
            raise
        except Exception as e:
            logger.error(f"Error ejecutando query DAX: {e}")
            raise PowerBIQueryError(f"Error en query: {str(e)}")

    def _parse_response(self, response_data: dict) -> List[Dict]:
        """
        Parsea la respuesta de Power BI executeQueries a lista de diccionarios.

        Estructura de respuesta:
        {
            "results": [
                {
                    "tables": [
                        {
                            "rows": [
                                {"Column1": value1, "Column2": value2, ...},
                                ...
                            ]
                        }
                    ]
                }
            ]
        }
        """
        try:
            results = response_data.get("results", [])
            if not results:
                return []

            tables = results[0].get("tables", [])
            if not tables:
                return []

            rows = tables[0].get("rows", [])
            return rows

        except Exception as e:
            logger.error(f"Error parseando respuesta DAX: {e}")
            return []

    def get_dataset_info(self) -> Dict:
        """Obtiene información del dataset para validación"""
        try:
            token = self.auth_service.get_access_token()

            url = (
                f"{self.POWERBI_API_URL}/groups/{self.group_id}"
                f"/datasets/{self.dataset_id}"
            )

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    f"Error obteniendo info del dataset: {response.status_code}"
                )
                return {}

        except Exception as e:
            logger.error(f"Error obteniendo info del dataset: {e}")
            return {}


# =============================================================================
# Power BI Alert Service (Main Service)
# =============================================================================


class PowerBIAlertService:
    """
    Servicio principal para procesar alertas de Power BI.
    Maneja múltiples definiciones de alertas por tenant.
    Integra con OpenAI para formateo y Telegram para notificaciones.
    """

    def __init__(self, global_config: PowerBIGlobalConfig = None):
        self.global_config = global_config or self._get_active_global_config()
        if not self.global_config:
            raise ValueError("No hay configuración global de Power BI activa")
        self._openai_service = None  # Lazy initialization

    def _get_active_global_config(self) -> Optional[PowerBIGlobalConfig]:
        """Obtiene la configuración global activa de Power BI"""
        return PowerBIGlobalConfig.objects.filter(is_active=True).first()

    @property
    def openai_service(self) -> Optional[OpenAIFormatterService]:
        """Inicialización lazy del servicio OpenAI"""
        if self._openai_service is None:
            try:
                self._openai_service = OpenAIFormatterService()
            except ValueError as e:
                logger.warning(f"OpenAI no configurado: {e}")
                self._openai_service = None
        return self._openai_service

    def process_all_pending_alerts(self) -> Dict:
        """
        Procesa todas las definiciones de alertas que están pendientes de verificación.

        Returns:
            Dict con estadísticas agregadas del procesamiento
        """
        start_time = time.time()
        results = {
            "total_definitions_checked": 0,
            "total_definitions_processed": 0,
            "total_alerts_created": 0,
            "total_alerts_sent": 0,
            "total_alerts_failed": 0,
            "by_company": {},
            "errors": [],
        }

        try:
            # Obtener todas las definiciones activas
            definitions = PowerBIAlertDefinition.objects.filter(
                is_active=True,
                company__is_active=True,
            ).select_related("company")

            results["total_definitions_checked"] = definitions.count()

            for definition in definitions:
                if definition.is_due_for_check():
                    try:
                        def_result = self._process_alert_definition(definition)
                        results["total_definitions_processed"] += 1
                        results["total_alerts_created"] += def_result.get(
                            "alerts_created", 0
                        )
                        results["total_alerts_sent"] += def_result.get("alerts_sent", 0)
                        results["total_alerts_failed"] += def_result.get(
                            "alerts_failed", 0
                        )

                        # Track por empresa
                        company_name = definition.company.name
                        if company_name not in results["by_company"]:
                            results["by_company"][company_name] = {
                                "definitions_processed": 0,
                                "alerts_created": 0,
                                "alerts_sent": 0,
                            }
                        results["by_company"][company_name][
                            "definitions_processed"
                        ] += 1
                        results["by_company"][company_name][
                            "alerts_created"
                        ] += def_result.get("alerts_created", 0)
                        results["by_company"][company_name][
                            "alerts_sent"
                        ] += def_result.get("alerts_sent", 0)

                    except Exception as e:
                        error_msg = f"{definition.name}: {str(e)}"
                        results["errors"].append(error_msg)
                        logger.error(f"Error procesando alerta {definition.name}: {e}")

            # Log global
            processing_time = time.time() - start_time
            self._log_global_processing(results, processing_time)

            logger.info(
                f"Procesamiento completado: {results['total_definitions_processed']} "
                f"definiciones, {results['total_alerts_created']} alertas creadas, "
                f"{results['total_alerts_sent']} enviadas"
            )

            return results

        except Exception as e:
            logger.error(f"Error en procesamiento global: {e}", exc_info=True)
            raise

    def _process_alert_definition(self, definition: PowerBIAlertDefinition) -> Dict:
        """
        Procesa una definición de alerta individual.

        Args:
            definition: Definición de alerta a procesar

        Returns:
            Dict con estadísticas del procesamiento
        """
        start_time = time.time()
        result = {
            "records_fetched": 0,
            "records_new": 0,
            "records_skipped": 0,
            "alerts_created": 0,
            "alerts_sent": 0,
            "alerts_failed": 0,
        }

        try:
            # Obtener valores con fallback a configuración global
            group_id = definition.get_group_id()
            dataset_id = definition.get_dataset_id()
            dax_query = definition.get_dax_query()

            if not group_id or not dataset_id:
                raise ValueError(
                    f"Falta Group ID o Dataset ID para {definition.name}. "
                    "Configura en la alerta o en la configuración global."
                )

            # Crear servicio de query con los parámetros de esta definición
            query_service = PowerBIQueryService(
                global_config=self.global_config,
                group_id=group_id,
                dataset_id=dataset_id,
            )

            # Ejecutar query DAX
            rows = query_service.execute_query(dax_query)
            result["records_fetched"] = len(rows)

            if not rows:
                logger.info(f"No hay registros para {definition.name}")
                definition.mark_as_checked()
                self._log_definition_processing(definition, result, time.time() - start_time)
                return result

            # Obtener IDs existentes para deduplicación
            existing_ids = set(
                PowerBIAlertInstance.objects.filter(
                    alert_definition=definition,
                ).values_list("powerbi_record_id", flat=True)
            )

            # Auto-detectar campo ID del primer registro
            id_field = self._detect_id_field(rows[0] if rows else {})

            # Procesar cada registro
            for row in rows:
                record_id = self._get_record_id(row, id_field)

                if not record_id:
                    logger.warning(f"Registro sin ID en {definition.name}: {row}")
                    result["records_skipped"] += 1
                    continue

                if record_id in existing_ids:
                    result["records_skipped"] += 1
                    continue

                result["records_new"] += 1

                try:
                    # Crear instancia de alerta
                    instance = self._create_alert_instance(definition, row, record_id)
                    if instance:
                        result["alerts_created"] += 1

                        # Enviar a Telegram
                        if self._send_to_telegram(instance, definition):
                            result["alerts_sent"] += 1
                        else:
                            result["alerts_failed"] += 1

                except Exception as e:
                    logger.error(
                        f"Error procesando registro {record_id} en {definition.name}: {e}"
                    )
                    result["alerts_failed"] += 1

            # Marcar como verificado y log
            definition.mark_as_checked()
            processing_time = time.time() - start_time
            self._log_definition_processing(definition, result, processing_time)

            logger.info(
                f"Procesada {definition.name}: {result['alerts_created']} creadas, "
                f"{result['alerts_sent']} enviadas"
            )

            return result

        except Exception as e:
            logger.error(f"Error en definición {definition.id}: {e}")
            # Log de error
            self._log_definition_processing(
                definition,
                {"error": str(e), **result},
                time.time() - start_time,
                status="error",
            )
            raise

    def _create_alert_instance(
        self,
        definition: PowerBIAlertDefinition,
        row: dict,
        record_id: str,
    ) -> Optional[PowerBIAlertInstance]:
        """
        Crea una instancia de alerta con formateo OpenAI.

        Args:
            definition: Definición de alerta
            row: Datos del registro de Power BI
            record_id: ID único del registro

        Returns:
            PowerBIAlertInstance creada o None si falla
        """
        try:
            # Formatear mensaje
            formatted_message = self._format_with_openai(definition, row)

            with transaction.atomic():
                instance = PowerBIAlertInstance.objects.create(
                    alert_definition=definition,
                    company=definition.company,
                    powerbi_record_id=record_id,
                    raw_data=row,
                    formatted_message=formatted_message,
                    priority=definition.default_priority,
                    status="pending",
                    processed_at=timezone.now(),
                )

            logger.debug(f"Instancia creada: {instance.id} para {definition.name}")
            return instance

        except Exception as e:
            logger.error(f"Error creando instancia: {e}")
            raise

    def _format_with_openai(
        self, definition: PowerBIAlertDefinition, row: dict
    ) -> str:
        """
        Formatea los datos del registro usando OpenAI.

        Args:
            definition: Definición de alerta (contiene template y ejemplo)
            row: Datos del registro de Power BI

        Returns:
            Mensaje formateado
        """
        template = definition.get_openai_template()
        example = definition.get_example_output()

        # Si no hay template y no hay OpenAI, usar formato básico
        if not template and not self.openai_service:
            return self._basic_format(definition, row)

        # Si hay OpenAI configurado, usarlo
        if self.openai_service:
            context = {
                "company_name": definition.company.name,
                "alert_name": definition.name,
                "priority": definition.default_priority,
                "timestamp": timezone.now().isoformat(),
            }

            return self.openai_service.format_alert(
                raw_data=row,
                template=template,
                example_output=example,
                context=context,
            )

        # Fallback
        return self._basic_format(definition, row)

    def _basic_format(self, definition: PowerBIAlertDefinition, row: dict) -> str:
        """Formato básico sin OpenAI"""
        priority_emoji = {
            "critical": "🚨",
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢",
        }.get(definition.default_priority, "📊")

        lines = [
            f"{priority_emoji} <b>{definition.name}</b>",
            f"<b>Empresa:</b> {definition.company.name}",
            "",
        ]

        for key, value in row.items():
            str_value = str(value)
            if len(str_value) > 100:
                str_value = str_value[:100] + "..."
            lines.append(f"<b>{key}:</b> {str_value}")

        return "\n".join(lines)

    def _detect_id_field(self, row: dict) -> Optional[str]:
        """
        Auto-detecta el campo ID en un registro de Power BI.
        Busca campos que contengan 'id' en el nombre.

        Prioridad:
        1. Campo que sea exactamente 'id' o '[id]'
        2. Campo que termine en '_id' o '[*_id]'
        3. Campo que contenga 'id' en cualquier parte
        4. Primer campo del registro (fallback)
        """
        if not row:
            return None

        keys = list(row.keys())

        # Buscar campo exacto 'id' o '[id]'
        for key in keys:
            key_lower = key.lower().strip('[]')
            if key_lower == 'id':
                return key

        # Buscar campos que terminen en _id
        for key in keys:
            key_lower = key.lower().strip('[]')
            if key_lower.endswith('_id') or key_lower.endswith('id_'):
                return key

        # Buscar campos que contengan 'id'
        for key in keys:
            key_lower = key.lower()
            if 'id' in key_lower:
                return key

        # Fallback: usar el primer campo
        return keys[0] if keys else None

    def _get_record_id(self, row: dict, id_field: Optional[str]) -> str:
        """
        Obtiene el ID único de un registro.
        Si no encuentra el campo ID, genera un hash de todos los valores.
        """
        import hashlib

        if id_field and id_field in row:
            value = row[id_field]
            if value:
                return str(value)

        # Fallback: generar hash de todos los valores
        content = str(sorted(row.items()))
        return hashlib.md5(content.encode()).hexdigest()

    def _send_to_telegram(
        self, instance: PowerBIAlertInstance, definition: PowerBIAlertDefinition
    ) -> bool:
        """
        Envía la alerta formateada a los chats de Telegram configurados.

        Args:
            instance: Instancia de alerta a enviar
            definition: Definición con los chats destinatarios

        Returns:
            True si se envió al menos a un chat, False en caso contrario
        """
        try:
            # Obtener chats activos para esta definición
            chats = definition.telegram_chats.filter(is_active=True)

            if not chats.exists():
                logger.warning(f"No hay chats configurados para {definition.name}")
                instance.status = "ignored"
                instance.error_message = "No hay chats configurados"
                instance.save()
                return False

            # Importar servicio de Telegram
            from telegram_bot.services import TelegramNotificationService

            success_count = 0
            errors = []

            # Guardar esquema original para restaurar
            original_schema = connection.schema_name

            try:
                # Cambiar a esquema público para acceder a TelegramChat
                connection.set_schema("public")

                service = TelegramNotificationService(company=definition.company)

                for chat in chats:
                    try:
                        sent = service._send_message_to_chat(
                            chat=chat,
                            message_text=instance.formatted_message,
                            subject=f"Power BI: {definition.name}",
                            message_type="powerbi_alert",
                        )
                        if sent:
                            success_count += 1
                    except Exception as e:
                        errors.append(f"Chat {chat.chat_id}: {str(e)}")
                        logger.error(f"Error enviando a chat {chat.chat_id}: {e}")

            finally:
                # Restaurar esquema
                if connection.schema_name != original_schema:
                    connection.set_schema(original_schema)

            # Actualizar estado de la instancia
            if success_count > 0:
                instance.mark_as_sent()
                logger.info(
                    f"Alerta {instance.id} enviada a {success_count}/{chats.count()} chats"
                )
                return True
            else:
                error_msg = "; ".join(errors) if errors else "No se pudo enviar"
                instance.mark_as_failed(error_msg)
                return False

        except Exception as e:
            logger.error(f"Error enviando notificación Telegram: {e}")
            instance.mark_as_failed(f"Error Telegram: {str(e)}")
            return False

    def _log_definition_processing(
        self,
        definition: PowerBIAlertDefinition,
        result: Dict,
        processing_time: float,
        status: str = None,
    ):
        """Registra el resultado del procesamiento de una definición"""
        try:
            if status is None:
                if result.get("alerts_failed", 0) > 0:
                    status = "warning"
                elif "error" in result:
                    status = "error"
                else:
                    status = "success"

            message = (
                f"Registros: {result.get('records_fetched', 0)} obtenidos, "
                f"{result.get('records_new', 0)} nuevos, "
                f"{result.get('records_skipped', 0)} omitidos. "
                f"Alertas: {result.get('alerts_created', 0)} creadas, "
                f"{result.get('alerts_sent', 0)} enviadas, "
                f"{result.get('alerts_failed', 0)} fallidas."
            )

            if "error" in result:
                message = f"Error: {result['error']}"

            PowerBIProcessingLog.objects.create(
                alert_definition=definition,
                status=status,
                message=message,
                records_fetched=result.get("records_fetched", 0),
                records_new=result.get("records_new", 0),
                records_skipped=result.get("records_skipped", 0),
                alerts_created=result.get("alerts_created", 0),
                alerts_sent=result.get("alerts_sent", 0),
                alerts_failed=result.get("alerts_failed", 0),
                processing_time=processing_time,
            )

        except Exception as e:
            logger.error(f"Error guardando log de procesamiento: {e}")

    def _log_global_processing(self, results: Dict, processing_time: float):
        """Registra el resultado del procesamiento global"""
        try:
            status = "success"
            if results.get("errors"):
                status = "warning"
            if results["total_definitions_processed"] == 0:
                status = "info"

            message = (
                f"Definiciones: {results['total_definitions_checked']} verificadas, "
                f"{results['total_definitions_processed']} procesadas. "
                f"Alertas: {results['total_alerts_created']} creadas, "
                f"{results['total_alerts_sent']} enviadas, "
                f"{results['total_alerts_failed']} fallidas."
            )

            if results.get("errors"):
                message += f" Errores: {len(results['errors'])}"

            PowerBIProcessingLog.objects.create(
                alert_definition=None,  # Log global
                status=status,
                message=message,
                records_fetched=results["total_definitions_checked"],
                records_new=results["total_definitions_processed"],
                alerts_created=results["total_alerts_created"],
                alerts_sent=results["total_alerts_sent"],
                alerts_failed=results["total_alerts_failed"],
                processing_time=processing_time,
                results_by_company=results.get("by_company", {}),
            )

        except Exception as e:
            logger.error(f"Error guardando log global: {e}")


# =============================================================================
# Utility Functions
# =============================================================================


def test_powerbi_connection(
    global_config: PowerBIGlobalConfig = None,
    group_id: str = None,
    dataset_id: str = None,
    dax_query: str = None,
) -> Dict:
    """
    Función de utilidad para probar la conexión a Power BI.

    Args:
        global_config: Configuración global (usa activa si no se proporciona)
        group_id: ID del workspace a probar
        dataset_id: ID del dataset a probar
        dax_query: Query DAX a probar (opcional)

    Returns:
        Dict con resultado del test
    """
    result = {
        "success": False,
        "auth": False,
        "dataset_info": None,
        "query_test": False,
        "records_found": 0,
        "error": None,
    }

    try:
        global_config = global_config or PowerBIGlobalConfig.objects.filter(
            is_active=True
        ).first()

        if not global_config:
            result["error"] = "No hay configuración global de Power BI activa"
            return result

        # Test autenticación
        auth_service = PowerBIAuthService(global_config)
        token = auth_service.get_access_token()
        result["auth"] = True
        logger.info("✓ Autenticación exitosa")

        # Test info del dataset (si se proporcionan IDs)
        if group_id and dataset_id:
            query_service = PowerBIQueryService(
                global_config=global_config,
                group_id=group_id,
                dataset_id=dataset_id,
            )

            dataset_info = query_service.get_dataset_info()
            result["dataset_info"] = dataset_info
            logger.info(f"✓ Dataset info: {dataset_info.get('name', 'N/A')}")

            # Test query
            if dax_query:
                try:
                    rows = query_service.execute_query(dax_query)
                    result["query_test"] = True
                    result["records_found"] = len(rows)
                    logger.info(f"✓ Query exitosa: {len(rows)} registros")
                except Exception as e:
                    result["query_error"] = str(e)
                    logger.warning(f"✗ Error en query: {e}")

        result["success"] = result["auth"]

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Error en test de conexión: {e}")

    return result


def test_openai_connection(api_key: str = None) -> Dict:
    """
    Función de utilidad para probar la conexión a OpenAI.

    Args:
        api_key: API key de OpenAI (usa settings si no se proporciona)

    Returns:
        Dict con resultado del test
    """
    result = {
        "success": False,
        "error": None,
    }

    try:
        service = OpenAIFormatterService(api_key=api_key)

        # Test con datos de ejemplo
        test_data = {"producto": "Test", "cantidad": 10, "precio": 100}
        formatted = service.format_alert(
            raw_data=test_data,
            context={"company_name": "Test", "alert_name": "Test Alert"},
        )

        result["success"] = True
        result["sample_output"] = formatted[:200]
        logger.info("✓ OpenAI test exitoso")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Error en test de OpenAI: {e}")

    return result
