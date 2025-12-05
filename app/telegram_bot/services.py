"""
Servicios para enviar alertas de Telegram
Adaptado para arquitectura multi-tenant con bot centralizado
"""

import logging
import requests
from django.utils import timezone
from django.db import connection
from .models import TelegramConfig, TelegramChat, TelegramMessage, TelegramRegistrationCode

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """
    Servicio para enviar notificaciones de Telegram
    Usa un bot centralizado (del esquema público) para enviar a chats específicos de empresas
    """

    def __init__(self, company=None):
        """
        Inicializar con la configuración centralizada del bot

        Args:
            company: Instancia de Company. Si no se proporciona, se intenta obtener del contexto actual.
        """
        self.company = company or self._get_current_company()
        self.config = self._get_bot_config()

        if not self.config:
            raise ValueError("No hay configuración de Telegram activa en el esquema público")

    def _get_current_company(self):
        """Obtiene la empresa actual basándose en el esquema"""
        from company.models import Company

        try:
            # Si estamos en un tenant, obtener la empresa
            if connection.schema_name != "public":
                return Company.objects.get(schema_name=connection.schema_name)
            return None
        except Company.DoesNotExist:
            return None

    def _get_bot_config(self):
        """Obtiene la configuración del bot desde el esquema público"""
        original_schema = connection.schema_name

        try:
            # Cambiar al esquema público para obtener la configuración
            connection.set_schema("public")

            # Obtener configuración activa
            config = TelegramConfig.objects.filter(is_active=True).first()

            return config

        except Exception as e:
            logger.error(f"Error obteniendo configuración del bot: {e}")
            return None
        finally:
            # Restaurar el esquema original
            connection.set_schema(original_schema)

    def send_powerbi_alert(self, alert_data, company=None):
        """
        Enviar alerta de Power BI a los chats de la empresa

        Args:
            alert_data: Diccionario con datos de la alerta:
                - subject: Asunto de la alerta
                - body: Cuerpo del mensaje
                - priority: Prioridad (low, medium, high, critical)
                - record_id: ID del registro en Power BI
            company: Instancia de Company (opcional, usa self.company por defecto)

        Returns:
            bool: True si se envió exitosamente a al menos un chat
        """
        target_company = company or self.company

        if not target_company:
            logger.warning("No se especificó empresa para enviar alerta de Power BI")
            return False

        # Guardar el esquema original
        original_schema = connection.schema_name

        try:
            # Cambiar al esquema público para acceder a TelegramChat
            connection.set_schema("public")

            # Obtener chats activos de la empresa que reciben alertas
            chats = TelegramChat.objects.filter(
                company=target_company, is_active=True, email_alerts=True
            )

            if not chats.exists():
                logger.warning(
                    f"No hay chats activos para la empresa {target_company.name}"
                )
                connection.set_schema(original_schema)
                return False

            # Crear mensaje
            message_text = self._format_powerbi_message(alert_data)

            # Enviar a todos los chats
            chats_list = list(chats)
            logger.info(f"Enviando alerta Power BI a {len(chats_list)} chats de {target_company.name}")

            success_count = 0
            for chat in chats_list:
                if self._send_message_to_chat(
                    chat=chat,
                    message_text=message_text,
                    subject=alert_data.get("subject", "Alerta Power BI"),
                    message_type="powerbi_alert",
                ):
                    success_count += 1

            logger.info(
                f"Alerta Power BI enviada a {success_count}/{len(chats_list)} chats de {target_company.name}"
            )

            connection.set_schema(original_schema)
            return success_count > 0

        except Exception as e:
            logger.error(f"Error enviando alerta de Power BI: {e}", exc_info=True)
            connection.set_schema(original_schema)
            return False
        finally:
            # Asegurar que siempre se restaure el esquema original
            if connection.schema_name != original_schema:
                connection.set_schema(original_schema)

    def send_system_alert(self, message, subject="Alerta del Sistema", company=None):
        """
        Enviar alerta del sistema a los chats de la empresa

        Args:
            message: Texto del mensaje
            subject: Asunto del mensaje
            company: Instancia de Company (opcional, usa self.company por defecto)

        Returns:
            bool: True si se envió exitosamente a al menos un chat
        """
        target_company = company or self.company

        if not target_company:
            logger.warning("No se especificó empresa para enviar alerta del sistema")
            return False

        # Guardar el esquema original
        original_schema = connection.schema_name

        try:
            # Cambiar al esquema público para acceder a TelegramChat
            connection.set_schema("public")

            # Obtener chats activos que reciben alertas del sistema
            chats = TelegramChat.objects.filter(
                company=target_company, is_active=True, system_alerts=True
            )

            if not chats.exists():
                logger.warning(
                    f"No hay chats para alertas del sistema en {target_company.name}"
                )
                connection.set_schema(original_schema)
                return False

            # Enviar a todos los chats
            success_count = 0
            for chat in chats:
                if self._send_message_to_chat(
                    chat=chat,
                    message_text=message,
                    subject=subject,
                    message_type="system_alert",
                ):
                    success_count += 1

            logger.info(
                f"Alerta del sistema enviada a {success_count}/{chats.count()} chats de {target_company.name}"
            )

            connection.set_schema(original_schema)
            return success_count > 0

        except Exception as e:
            logger.error(f"Error enviando alerta del sistema: {e}", exc_info=True)
            connection.set_schema(original_schema)
            return False
        finally:
            # Asegurar que siempre se restaure el esquema original
            if connection.schema_name != original_schema:
                connection.set_schema(original_schema)

    def _send_message_to_chat(
        self,
        chat,
        message_text,
        subject,
        message_type="manual",
    ):
        """
        Envía un mensaje a un chat específico y registra el envío

        Args:
            chat: Instancia de TelegramChat
            message_text: Texto del mensaje a enviar
            subject: Asunto del mensaje
            message_type: Tipo de mensaje (powerbi_alert, system_alert, manual)

        Returns:
            bool: True si el mensaje se envió exitosamente
        """
        # Crear registro del mensaje
        telegram_message = TelegramMessage.objects.create(
            company=chat.company,
            chat=chat,
            message_type=message_type,
            subject=subject,
            message=message_text,
            status="pending",
        )

        try:
            # Usar el bot específico del chat si está definido
            bot_to_use = chat.bot if chat.bot else self.config

            if not bot_to_use:
                telegram_message.status = "failed"
                telegram_message.error_message = "No hay bot configurado para este chat"
                telegram_message.save()
                logger.error(f"No hay bot configurado para el chat {chat.chat_id}")
                return False

            # Enviar mensaje usando el bot del chat
            success = self._send_message_with_bot(bot_to_use, chat.chat_id, message_text)

            if success:
                telegram_message.status = "sent"
                telegram_message.sent_at = timezone.now()
                logger.info(f"Mensaje enviado exitosamente a chat {chat.chat_id} usando bot {bot_to_use.name}")
            else:
                telegram_message.status = "failed"
                telegram_message.error_message = "Error enviando mensaje (sin detalles)"
                logger.error(f"Error enviando mensaje a chat {chat.chat_id}")

            telegram_message.save()
            return success

        except Exception as e:
            telegram_message.status = "failed"
            telegram_message.error_message = str(e)
            telegram_message.save()
            logger.error(f"Error enviando mensaje a chat {chat.chat_id}: {e}")
            return False

    def _format_powerbi_message(self, alert_data):
        """Formatear mensaje de Power BI para Telegram"""
        import html

        # Escapar HTML para evitar errores de parsing
        subject = html.escape(alert_data.get("subject", "Sin asunto"))
        body = html.escape(alert_data.get("body", ""))
        priority = alert_data.get("priority", "medium")

        # Determinar emoji por prioridad
        priority_emojis = {
            "critical": "🚨",
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢",
        }
        emoji = priority_emojis.get(priority, "📊")

        # Determinar texto de prioridad
        priority_labels = {
            "critical": "CRÍTICA",
            "high": "ALTA",
            "medium": "MEDIA",
            "low": "BAJA",
        }
        priority_text = priority_labels.get(priority, "MEDIA")

        message = f"{emoji} <b>Alerta Power BI - Prioridad {priority_text}</b>\n\n"
        message += f"<b>Asunto:</b> {subject}\n"

        if body:
            # Limitar cuerpo a 500 caracteres
            body_preview = body[:500] + "..." if len(body) > 500 else body
            message += f"\n<b>Detalle:</b>\n<i>{body_preview}</i>"

        # Agregar info de la empresa
        if self.company:
            message += f"\n\n<b>Empresa:</b> {self.company.name}"

        return message

    def _send_message(self, chat_id, text):
        """
        Enviar mensaje a un chat específico usando el bot centralizado

        Args:
            chat_id: ID del chat de Telegram
            text: Texto del mensaje

        Returns:
            bool: True si el mensaje se envió exitosamente
        """
        return self._send_message_with_bot(self.config, chat_id, text)

    def _send_message_with_bot(self, bot_config, chat_id, text):
        """
        Enviar mensaje a un chat específico usando un bot específico

        Args:
            bot_config: Instancia de TelegramConfig
            chat_id: ID del chat de Telegram
            text: Texto del mensaje

        Returns:
            bool: True si el mensaje se envió exitosamente
        """
        try:
            url = f"https://api.telegram.org/bot{bot_config.bot_token}/sendMessage"
            data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

            response = requests.post(url, data=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    logger.info(f"Mensaje enviado exitosamente a chat {chat_id} usando bot {bot_config.name}")
                    return True
                else:
                    logger.error(
                        f"Error en respuesta de Telegram: {result.get('description')}"
                    )
                    return False
            else:
                logger.error(
                    f"Error HTTP al enviar mensaje a chat {chat_id}: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Excepción al enviar mensaje a chat {chat_id}: {e}")
            return False


class TelegramService:
    """
    Wrapper del servicio de Telegram para compatibilidad con código existente
    """

    def __init__(self, company=None):
        """Inicializar el servicio"""
        try:
            self.company = company
            self.notification_service = TelegramNotificationService(company=company)
        except ValueError as e:
            logger.warning(f"No se pudo inicializar servicio de Telegram: {e}")
            self.notification_service = None

    def send_message(self, chat_id, message, priority="medium"):
        """
        Enviar mensaje directo a un chat específico

        Args:
            chat_id: ID del chat
            message: Texto del mensaje
            priority: Prioridad del mensaje

        Returns:
            dict: Resultado del envío
        """
        try:
            if not self.notification_service:
                logger.warning("Servicio de Telegram no disponible")
                return {"status": "error", "message": "No hay configuración activa"}

            # Intentar enviar el mensaje directamente
            success = self.notification_service._send_message(chat_id, message)

            if success:
                return {
                    "status": "success",
                    "chat_id": chat_id,
                    "message": "Mensaje enviado exitosamente",
                }
            else:
                return {
                    "status": "error",
                    "chat_id": chat_id,
                    "message": "Error enviando mensaje",
                }

        except Exception as e:
            logger.error(f"Error en TelegramService.send_message: {e}")
            return {"status": "error", "message": str(e)}

    def send_powerbi_alert(self, alert_data):
        """
        Enviar alerta de Power BI usando el servicio principal

        Args:
            alert_data: Diccionario con datos de la alerta

        Returns:
            bool: True si el mensaje se envió exitosamente
        """
        try:
            if not self.notification_service:
                return False

            return self.notification_service.send_powerbi_alert(alert_data)

        except Exception as e:
            logger.error(f"Error enviando alerta de Power BI: {e}")
            return False


class TelegramRegistrationService:
    """
    Servicio para gestionar el registro de chats usando códigos
    """

    @staticmethod
    def register_chat_with_code(code_str, chat_data):
        """
        Valida un código de registro y crea automáticamente el chat

        Args:
            code_str: Código de registro (string)
            chat_data: Diccionario con datos del chat de Telegram:
                - chat_id: ID del chat
                - chat_type: Tipo de chat (private, group, supergroup, channel)
                - username: Username del chat (opcional)
                - title: Título del grupo/canal (opcional)

        Returns:
            dict: Resultado con estructura:
                {
                    'success': bool,
                    'message': str,
                    'chat': TelegramChat (si success=True),
                    'error_code': str (si success=False)
                }
        """
        try:
            # Normalizar código (mayúsculas, sin espacios)
            code_str = code_str.strip().upper()

            # Buscar código
            try:
                registration_code = TelegramRegistrationCode.objects.select_related(
                    'company', 'used_by_chat'
                ).get(code=code_str)
            except TelegramRegistrationCode.DoesNotExist:
                return {
                    'success': False,
                    'message': f'❌ Código inválido: {code_str}',
                    'error_code': 'CODE_NOT_FOUND'
                }

            # Validar que el código no esté usado
            if registration_code.is_used:
                msg = f'❌ Este código ya fue usado'
                if registration_code.used_by_chat:
                    msg += f' por el chat "{registration_code.used_by_chat.name}"'
                return {
                    'success': False,
                    'message': msg,
                    'error_code': 'CODE_ALREADY_USED'
                }

            # Validar que el código no esté expirado
            if registration_code.is_expired():
                return {
                    'success': False,
                    'message': f'❌ Este código expiró el {registration_code.expires_at.strftime("%d/%m/%Y %H:%M")}',
                    'error_code': 'CODE_EXPIRED'
                }

            # Verificar que el chat no esté ya registrado
            chat_id = chat_data.get('chat_id')

            # Verificar si el chat ya existe para ESTA empresa
            existing_chat_same_company = TelegramChat.objects.filter(
                chat_id=chat_id,
                company=registration_code.company
            ).first()

            if existing_chat_same_company:
                return {
                    'success': False,
                    'message': f'❌ Este chat ya está registrado como "{existing_chat_same_company.name}" para tu empresa.\n\n💡 Si quieres actualizar la configuración, elimina el chat antiguo desde el admin primero.',
                    'error_code': 'CHAT_ALREADY_REGISTERED_SAME_COMPANY'
                }

            # Verificar si el chat ya existe para OTRA empresa
            existing_chat_other_company = TelegramChat.objects.filter(chat_id=chat_id).first()
            if existing_chat_other_company:
                return {
                    'success': False,
                    'message': f'❌ Este chat ya está registrado para la empresa "{existing_chat_other_company.company.name}".\n\nUn chat no puede estar registrado en múltiples empresas.',
                    'error_code': 'CHAT_ALREADY_REGISTERED_OTHER_COMPANY'
                }

            # Obtener el bot activo
            original_schema = connection.schema_name
            try:
                connection.set_schema("public")
                active_bot = TelegramConfig.objects.filter(is_active=True).first()
            finally:
                connection.set_schema(original_schema)

            if not active_bot:
                return {
                    'success': False,
                    'message': '❌ Error: No hay bot activo configurado',
                    'error_code': 'NO_ACTIVE_BOT'
                }

            # Crear el chat automáticamente
            chat_type = chat_data.get('chat_type', 'private')
            username = chat_data.get('username', '')
            title = chat_data.get('title', '')

            # Generar nombre descriptivo para el chat
            if title:
                chat_name = title
            elif username:
                chat_name = f"@{username}"
            else:
                chat_name = f"Chat {chat_id}"

            new_chat = TelegramChat.objects.create(
                company=registration_code.company,
                bot=active_bot,
                name=chat_name,
                chat_id=chat_id,
                chat_type=chat_type,
                username=username,
                title=title,
                alert_level='all',
                email_alerts=True,
                system_alerts=False,
                is_active=True,
            )

            # Marcar código como usado
            registration_code.mark_as_used(new_chat)

            # Si el código está asignado a un usuario específico, actualizar su telegram_chat_id
            if registration_code.assigned_to_user_email:
                try:
                    # Cambiar al schema del tenant para actualizar el usuario
                    tenant_schema = registration_code.company.schema_name
                    connection.set_schema(tenant_schema)

                    from user.models import User
                    user = User.objects.filter(
                        email=registration_code.assigned_to_user_email,
                        company=registration_code.company
                    ).first()

                    if user:
                        user.telegram_chat_id = str(chat_id)
                        user.save()
                        logger.info(
                            f'Usuario {user.email} actualizado con telegram_chat_id: {chat_id}'
                        )
                    else:
                        logger.warning(
                            f'No se encontró usuario con email {registration_code.assigned_to_user_email} '
                            f'en empresa {registration_code.company.name}'
                        )

                    # Volver al schema público
                    connection.set_schema('public')
                except Exception as e:
                    logger.error(f'Error actualizando usuario con telegram_chat_id: {e}')
                    # Volver al schema público en caso de error
                    connection.set_schema('public')

            logger.info(
                f'Chat {chat_id} registrado exitosamente para empresa {registration_code.company.name} '
                f'usando código {code_str}'
            )

            return {
                'success': True,
                'message': f'✅ ¡Registro exitoso!\n\nTu chat "{chat_name}" ha sido registrado para la empresa {registration_code.company.name}.\n\nYa comenzarás a recibir notificaciones.',
                'chat': new_chat,
            }

        except Exception as e:
            logger.error(f'Error registrando chat con código {code_str}: {e}', exc_info=True)
            return {
                'success': False,
                'message': f'❌ Error interno del servidor: {str(e)}',
                'error_code': 'INTERNAL_ERROR'
            }
