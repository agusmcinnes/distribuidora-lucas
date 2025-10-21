"""
Signals para el modelo User
"""

import logging
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
from django.db import connection
from .models import User

logger = logging.getLogger(__name__)


@receiver(pre_delete, sender=User)
def delete_telegram_chat_on_user_delete(sender, instance, **kwargs):
    """
    Elimina el chat de Telegram cuando se elimina un usuario
    """
    if not instance.telegram_chat_id:
        return  # Usuario sin chat de Telegram

    try:
        original_schema = connection.schema_name

        # Cambiar al esquema público para eliminar el chat
        connection.set_schema('public')

        from telegram_bot.models import TelegramChat

        # Buscar el chat por chat_id
        chat = TelegramChat.objects.filter(
            chat_id=instance.telegram_chat_id,
            company=instance.company
        ).first()

        if chat:
            logger.info(
                f'🗑️  Eliminando chat de Telegram {chat.name} ({chat.chat_id}) '
                f'asociado al usuario {instance.name} ({instance.email})'
            )
            chat.delete()
            logger.info(f'✅ Chat de Telegram eliminado exitosamente')
        else:
            logger.warning(
                f'⚠️  No se encontró chat de Telegram con ID {instance.telegram_chat_id} '
                f'para el usuario {instance.name}'
            )

        # Volver al schema original
        connection.set_schema(original_schema)

    except Exception as e:
        logger.error(f'❌ Error eliminando chat de Telegram al eliminar usuario: {e}')
        # Volver al schema original en caso de error
        if connection.schema_name != original_schema:
            connection.set_schema(original_schema)
