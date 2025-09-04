"""
Servicios simplificados para enviar alertas de Telegram
"""

import logging
import requests
from django.utils import timezone
from .models import TelegramConfig, TelegramChat

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """
    Servicio simplificado para enviar notificaciones de Telegram
    """

    def __init__(self):
        """Inicializar con la configuración activa"""
        self.config = TelegramConfig.objects.filter(is_active=True).first()
        if not self.config:
            raise ValueError("No hay configuración de Telegram activa")

    def send_email_alert(self, email):
        """
        Enviar alerta por nuevo email
        """
        try:
            # Obtener todos los chats activos
            chats = TelegramChat.objects.filter(is_active=True)
            
            if not chats.exists():
                logger.warning("No hay chats activos para enviar alertas")
                return False

            # Crear mensaje
            message = self._format_email_message(email)
            
            # Enviar a todos los chats
            success = True
            for chat in chats:
                if not self._send_message(chat.chat_id, message):
                    success = False
                    
            return success
            
        except Exception as e:
            logger.error(f"Error enviando alerta de email: {e}")
            return False

    def _format_email_message(self, email):
        """Formatear mensaje de email"""
        import html
        
        # Escapar HTML para evitar errores de parsing
        sender = html.escape(email.sender) if email.sender else "Desconocido"
        subject = html.escape(email.subject) if email.subject else "Sin asunto"
        
        # Determinar prioridad por palabras clave
        priority = "ALTA" if any(word in email.subject.lower() for word in 
                               ["urgente", "importante", "critico", "emergencia"]) else "NORMAL"
        
        emoji = "🚨" if priority == "ALTA" else "📧"
        
        message = f"{emoji} <b>Nuevo Email - Prioridad {priority}</b>\n\n"
        message += f"<b>De:</b> {sender}\n"
        message += f"<b>Asunto:</b> {subject}\n"
        message += f"<b>Hora:</b> {timezone.now().strftime('%H:%M:%S %d/%m/%Y')}\n"
        
        # Preview del cuerpo (máximo 200 caracteres)
        if email.body:
            body_preview = html.escape(email.body)
            preview = body_preview[:200] + "..." if len(body_preview) > 200 else body_preview
            message += f"\n<b>Vista previa:</b>\n<i>{preview}</i>"
            
        return message

    def _send_message(self, chat_id, text):
        """Enviar mensaje a un chat específico"""
        try:
            url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Mensaje enviado exitosamente a chat {chat_id}")
                return True
            else:
                logger.error(f"Error enviando mensaje a chat {chat_id}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error enviando mensaje a chat {chat_id}: {e}")
            return False
