"""
Comando para configurar Telegram automáticamente desde variables de entorno
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from telegram_bot.models import TelegramConfig, TelegramChat


class Command(BaseCommand):
    help = "Configura Telegram automáticamente desde variables de entorno"

    def handle(self, *args, **options):
        self.stdout.write("🔧 Configurando Telegram...")
        
        # Crear o actualizar configuración del bot
        bot_config, created = TelegramConfig.objects.get_or_create(
            name="Distribuidora Lucas Bot",
            defaults={
                "bot_token": settings.TELEGRAM_BOT_TOKEN,
                "is_active": True
            }
        )
        
        if not created:
            bot_config.bot_token = settings.TELEGRAM_BOT_TOKEN
            bot_config.is_active = True
            bot_config.save()
            
        action = "creada" if created else "actualizada"
        self.stdout.write(f"✅ Configuración del bot {action}: {bot_config.name}")
        
        # Crear o actualizar chat
        chat_config, created = TelegramChat.objects.get_or_create(
            chat_id=settings.TELEGRAM_CHAT_ID,
            defaults={
                "name": "Distribuidora Lucas Chat",
                "chat_type": "private",
                "email_alerts": True,
                "system_alerts": True,
                "is_active": True
            }
        )
        
        if not created:
            chat_config.name = "Distribuidora Lucas Chat"
            chat_config.email_alerts = True
            chat_config.system_alerts = True
            chat_config.is_active = True
            chat_config.save()
            
        action = "creado" if created else "actualizado"
        self.stdout.write(f"✅ Chat {action}: {chat_config.name} (ID: {chat_config.chat_id})")
        
        self.stdout.write("🎉 Telegram configurado exitosamente!")
        self.stdout.write("📧 El sistema enviará alertas automáticamente cuando lleguen nuevos emails.")
