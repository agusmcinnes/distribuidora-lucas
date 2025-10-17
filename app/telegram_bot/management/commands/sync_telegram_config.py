"""
Comando para sincronizar la configuración de Telegram desde .env al modelo TelegramConfig
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from telegram_bot.models import TelegramConfig


class Command(BaseCommand):
    help = "Sincroniza la configuración de Telegram desde .env al modelo TelegramConfig"

    def handle(self, *args, **options):
        # Asegurarse de estar en esquema público
        original_schema = connection.schema_name
        connection.set_schema("public")

        try:
            # Obtener token del .env
            bot_token = settings.TELEGRAM_BOT_TOKEN

            if not bot_token:
                self.stdout.write(
                    self.style.ERROR(
                        "❌ No se encontró TELEGRAM_BOT_TOKEN en el archivo .env"
                    )
                )
                self.stdout.write(
                    self.style.WARNING(
                        "   Agrega TELEGRAM_BOT_TOKEN=tu_token_aqui en el archivo .env"
                    )
                )
                return

            # Buscar o crear la configuración
            config, created = TelegramConfig.objects.get_or_create(
                name="Bot Principal",
                defaults={
                    "bot_token": bot_token,
                    "is_active": True,
                },
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Configuración de Telegram creada exitosamente"
                    )
                )
                self.stdout.write(f"   Nombre: {config.name}")
                self.stdout.write(f"   Token: {bot_token[:20]}...")
                self.stdout.write(f"   Estado: Activo")
            else:
                # Actualizar si ya existe
                updated = False
                if config.bot_token != bot_token:
                    config.bot_token = bot_token
                    updated = True

                if not config.is_active:
                    config.is_active = True
                    updated = True

                if updated:
                    config.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Configuración de Telegram actualizada"
                        )
                    )
                    self.stdout.write(f"   Nombre: {config.name}")
                    self.stdout.write(f"   Token: {bot_token[:20]}...")
                    self.stdout.write(f"   Estado: Activo")
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Configuración de Telegram ya está sincronizada"
                        )
                    )
                    self.stdout.write(f"   Nombre: {config.name}")
                    self.stdout.write(f"   Estado: {'Activo' if config.is_active else 'Inactivo'}")

            # Verificar el bot
            self.stdout.write("\n🔍 Verificando conexión con Telegram...")
            if self._verify_bot(bot_token):
                self.stdout.write(
                    self.style.SUCCESS("✅ Bot de Telegram conectado correctamente")
                )
            else:
                self.stdout.write(
                    self.style.ERROR("❌ No se pudo conectar con el bot de Telegram")
                )
                self.stdout.write(
                    self.style.WARNING("   Verifica que el token sea correcto")
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error al sincronizar configuración: {str(e)}")
            )
        finally:
            # Restaurar esquema original
            connection.set_schema(original_schema)

    def _verify_bot(self, bot_token):
        """Verifica que el bot esté funcionando"""
        try:
            import requests

            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    bot_info = data.get("result", {})
                    self.stdout.write(
                        f"   🤖 Bot: @{bot_info.get('username', 'N/A')}"
                    )
                    self.stdout.write(
                        f"   📝 Nombre: {bot_info.get('first_name', 'N/A')}"
                    )
                    return True

            return False

        except Exception:
            return False
