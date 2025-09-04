"""
Comando para configuración inicial del bot de Telegram
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from telegram_bot.models import TelegramConfig, TelegramChat
from telegram_bot.services import TelegramService
from company.models import Company


class Command(BaseCommand):
    help = "Configuración inicial del bot de Telegram"

    def add_arguments(self, parser):
        parser.add_argument("--token", type=str, help="Token del bot de Telegram")
        parser.add_argument(
            "--chat-id", type=int, help="ID del chat por defecto para alertas"
        )
        parser.add_argument(
            "--chat-name",
            type=str,
            default="Chat Principal",
            help="Nombre descriptivo para el chat",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("🤖 Configuración inicial del bot de Telegram")
        )
        self.stdout.write("=" * 60)

        # Usar token del comando o del .env
        token = options["token"] or settings.TELEGRAM_BOT_TOKEN
        if not token:
            raise CommandError(
                "Token requerido. Proporciona --token o configura TELEGRAM_BOT_TOKEN en .env"
            )

        # Usar chat_id del comando o del .env
        chat_id = options["chat_id"]
        if not chat_id:
            try:
                chat_id = int(settings.TELEGRAM_DEFAULT_CHAT_ID)
            except (ValueError, TypeError):
                pass

        if not chat_id:
            raise CommandError(
                "Chat ID requerido. Proporciona --chat-id o configura TELEGRAM_DEFAULT_CHAT_ID en .env"
            )

        try:
            # 1. Crear o actualizar configuración del bot
            self.stdout.write("\n1️⃣ Configurando bot...")
            config, created = TelegramConfig.objects.get_or_create(
                name="Default Bot", defaults={"bot_token": token, "is_active": True}
            )

            if not created:
                config.bot_token = token
                config.is_active = True
                config.save()

            # 2. Probar conexión con el bot
            self.stdout.write("2️⃣ Probando conexión...")
            telegram_service = TelegramService(config)
            bot_info = telegram_service.get_bot_info()

            if not bot_info.get("ok"):
                raise CommandError(
                    f'Error conectando con el bot: {bot_info.get("description")}'
                )

            bot_data = bot_info["result"]
            self.stdout.write(
                self.style.SUCCESS(f'   ✅ Bot conectado: @{bot_data.get("username")}')
            )

            # 3. Crear o actualizar chat
            self.stdout.write("3️⃣ Configurando chat...")
            chat, created = TelegramChat.objects.get_or_create(
                chat_id=chat_id,
                defaults={
                    "name": options["chat_name"],
                    "chat_type": "private",
                    "alert_level": "all",
                    "email_alerts": True,
                    "system_alerts": True,
                    "is_active": True,
                },
            )

            if not created:
                chat.name = options["chat_name"]
                chat.email_alerts = True
                chat.is_active = True
                chat.save()

            # 4. Probar envío de mensaje
            self.stdout.write("4️⃣ Probando envío de mensaje...")
            try:
                test_message = (
                    "🎉 <b>¡Bot configurado correctamente!</b>\n\n"
                    "Este chat está configurado para recibir alertas de nuevos emails.\n\n"
                    f"🤖 Bot: @{bot_data.get('username')}\n"
                    f"💬 Chat: {chat.name}\n"
                    f"🆔 ID: <code>{chat_id}</code>"
                )

                response = telegram_service.send_message(
                    chat_id=chat_id, text=test_message
                )

                if response.get("ok"):
                    self.stdout.write(
                        self.style.SUCCESS("   ✅ Mensaje de prueba enviado")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'   ⚠️ Error enviando mensaje: {response.get("description")}'
                        )
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"   ⚠️ Error enviando mensaje: {str(e)}")
                )

            # 5. Resumen de configuración
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("✅ CONFIGURACIÓN COMPLETADA"))
            self.stdout.write("=" * 60)
            self.stdout.write(
                f'🤖 Bot: @{bot_data.get("username")} (ID: {bot_data.get("id")})'
            )
            self.stdout.write(f"💬 Chat: {chat.name} (ID: {chat_id})")
            self.stdout.write(
                f'📧 Alertas de email: {"✅" if chat.email_alerts else "❌"}'
            )
            self.stdout.write(
                f'🔧 Alertas del sistema: {"✅" if chat.system_alerts else "❌"}'
            )
            self.stdout.write(f"📊 Nivel de alertas: {chat.get_alert_level_display()}")

            # 6. Próximos pasos
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("📋 PRÓXIMOS PASOS:")
            self.stdout.write("=" * 60)
            self.stdout.write("1. El bot ya está configurado y funcionando")
            self.stdout.write(
                "2. Las alertas se enviarán automáticamente cuando lleguen emails"
            )
            self.stdout.write("3. Puedes configurar más chats desde el admin de Django")
            self.stdout.write(
                "4. Para webhook (producción): python manage.py setup_telegram_webhook --url https://tudominio.com/telegram/webhook/"
            )
            self.stdout.write(
                "5. Ejecuta: python manage.py test_telegram_bot --test-all (para probar todos los chats)"
            )

        except Exception as e:
            raise CommandError(f"Error en configuración: {str(e)}")
