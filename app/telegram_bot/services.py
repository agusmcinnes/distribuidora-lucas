"""
Servicios para enviar alertas de Telegram
Adaptado para arquitectura multi-tenant con bot centralizado
"""

import logging
import requests
from django.utils import timezone
from django.db import connection
from .models import TelegramConfig, TelegramChat, TelegramMessage

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

    def send_email_alert(self, email, company=None):
        """
        Enviar alerta por nuevo email a los chats de la empresa

        Args:
            email: Instancia de ReceivedEmail
            company: Instancia de Company (opcional, usa self.company por defecto)

        Returns:
            bool: True si se envió exitosamente a al menos un chat
        """
        target_company = company or self.company

        if not target_company:
            logger.warning("No se especificó empresa para enviar alerta")
            return False

        try:
            # Obtener chats activos de la empresa
            chats = TelegramChat.objects.filter(
                company=target_company, is_active=True, email_alerts=True
            )

            if not chats.exists():
                logger.warning(
                    f"No hay chats activos para la empresa {target_company.name}"
                )
                return False

            # Crear mensaje
            message_text = self._format_email_message(email)

            # Enviar a todos los chats
            success_count = 0
            for chat in chats:
                if self._send_message_to_chat(
                    chat=chat,
                    message_text=message_text,
                    subject=f"Email de {email.sender}",
                    message_type="email_alert",
                    email_subject=email.subject,
                    email_sender=email.sender,
                    email_priority=email.priority,
                ):
                    success_count += 1

            logger.info(
                f"Alerta de email enviada a {success_count}/{chats.count()} chats de {target_company.name}"
            )

            # Marcar email como enviado si se envió a al menos un chat
            if success_count > 0:
                email.mark_as_sent()
                return True

            return False

        except Exception as e:
            logger.error(f"Error enviando alerta de email: {e}", exc_info=True)
            email.mark_as_failed(f"Error: {str(e)}")
            return False

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

        try:
            # Obtener chats activos que reciben alertas del sistema
            chats = TelegramChat.objects.filter(
                company=target_company, is_active=True, system_alerts=True
            )

            if not chats.exists():
                logger.warning(
                    f"No hay chats para alertas del sistema en {target_company.name}"
                )
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

            return success_count > 0

        except Exception as e:
            logger.error(f"Error enviando alerta del sistema: {e}", exc_info=True)
            return False

    def _send_message_to_chat(
        self,
        chat,
        message_text,
        subject,
        message_type="manual",
        email_subject=None,
        email_sender=None,
        email_priority=None,
    ):
        """
        Envía un mensaje a un chat específico y registra el envío

        Args:
            chat: Instancia de TelegramChat
            message_text: Texto del mensaje a enviar
            subject: Asunto del mensaje
            message_type: Tipo de mensaje (email_alert, system_alert, manual)
            email_subject: Asunto del email original (opcional)
            email_sender: Remitente del email original (opcional)
            email_priority: Prioridad del email original (opcional)

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
            email_subject=email_subject,
            email_sender=email_sender,
            email_priority=email_priority,
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

    def _format_email_message(self, email):
        """Formatear mensaje de email para Telegram"""
        import html

        # Escapar HTML para evitar errores de parsing
        sender = html.escape(email.sender) if email.sender else "Desconocido"
        subject = html.escape(email.subject) if email.subject else "Sin asunto"

        # Determinar emoji por prioridad
        priority_emojis = {
            "critical": "🚨",
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢",
        }
        emoji = priority_emojis.get(email.priority, "📧")

        # Determinar texto de prioridad
        priority_text = email.get_priority_display().upper()

        message = f"{emoji} <b>Nuevo Email - Prioridad {priority_text}</b>\n\n"
        message += f"<b>De:</b> {sender}\n"
        message += f"<b>Asunto:</b> {subject}\n"
        message += f"<b>Fecha:</b> {email.received_date.strftime('%H:%M:%S %d/%m/%Y')}\n"

        # Preview del cuerpo (máximo 200 caracteres)
        if email.body:
            body_preview = html.escape(email.body)
            preview = (
                body_preview[:200] + "..." if len(body_preview) > 200 else body_preview
            )
            message += f"\n<b>Vista previa:</b>\n<i>{preview}</i>"

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

    def send_email_alert(self, email):
        """
        Enviar alerta por nuevo email usando el servicio principal

        Args:
            email: Instancia de ReceivedEmail

        Returns:
            bool: True si el mensaje se envió exitosamente
        """
        try:
            if not self.notification_service:
                return False

            return self.notification_service.send_email_alert(email)

        except Exception as e:
            logger.error(f"Error enviando alerta de email: {e}")
            return False
