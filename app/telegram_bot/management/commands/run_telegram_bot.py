"""
Comando para ejecutar el bot de Telegram en modo polling
Responde a comandos como /get_chat_id
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import time
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ejecuta el bot de Telegram para responder a comandos (/get_chat_id)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--daemon",
            action="store_true",
            help="Ejecutar en modo daemon (loop continuo)",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=2,
            help="Intervalo en segundos entre polls (default: 2)",
        )

    def handle(self, *args, **options):
        daemon_mode = options.get("daemon", True)  # Por defecto daemon
        interval = options.get("interval", 2)

        # Obtener configuración del bot desde el esquema público
        from telegram_bot.models import TelegramConfig
        from django.db import connection

        # Asegurarse de estar en esquema público
        original_schema = connection.schema_name
        connection.set_schema("public")

        try:
            config = TelegramConfig.objects.filter(is_active=True).first()

            if not config:
                self.stdout.write(
                    self.style.ERROR("❌ No hay configuración de Telegram activa")
                )
                return

            self.stdout.write(
                self.style.SUCCESS(f"✅ Bot configurado: {config.name}")
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"🤖 Iniciando bot en modo {'daemon' if daemon_mode else 'single'}..."
                )
            )

            # Iniciar polling
            self._run_polling(config, daemon_mode, interval)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {str(e)}"))
        finally:
            # Restaurar esquema original
            connection.set_schema(original_schema)

    def _run_polling(self, config, daemon_mode, interval):
        """Ejecuta el bot en modo polling"""
        base_url = f"https://api.telegram.org/bot{config.bot_token}"
        offset = None

        self.stdout.write(
            self.style.SUCCESS("🔄 Bot escuchando comandos...")
        )
        self.stdout.write(
            self.style.WARNING(
                "💡 Los usuarios pueden enviar /get_chat_id en sus grupos para obtener el Chat ID"
            )
        )
        self.stdout.write(
            self.style.WARNING("⏸️  Presiona Ctrl+C para detener el bot")
        )
        self.stdout.write("")

        try:
            while True:
                try:
                    # Obtener updates
                    params = {"timeout": 30, "offset": offset}
                    response = requests.get(
                        f"{base_url}/getUpdates", params=params, timeout=35
                    )

                    if response.status_code != 200:
                        self.stdout.write(
                            self.style.ERROR(
                                f"❌ Error en API: {response.status_code}"
                            )
                        )
                        time.sleep(interval)
                        continue

                    data = response.json()

                    if not data.get("ok"):
                        self.stdout.write(
                            self.style.ERROR(
                                f"❌ Error en respuesta: {data.get('description')}"
                            )
                        )
                        time.sleep(interval)
                        continue

                    updates = data.get("result", [])

                    # Procesar cada update
                    for update in updates:
                        offset = update["update_id"] + 1
                        self._process_update(config, update)

                    # Si no es daemon, salir después del primer batch
                    if not daemon_mode and len(updates) == 0:
                        self.stdout.write(
                            self.style.SUCCESS("✅ No hay más updates. Terminando...")
                        )
                        break

                    if not daemon_mode and len(updates) > 0:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✅ Procesados {len(updates)} updates. Terminando..."
                            )
                        )
                        break

                    # Pequeña pausa en modo daemon
                    if daemon_mode and len(updates) == 0:
                        time.sleep(interval)

                except requests.exceptions.Timeout:
                    # Timeout es normal en long polling
                    continue
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"❌ Error en polling: {str(e)}")
                    )
                    time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n\n🛑 Bot detenido por el usuario"))

    def _process_update(self, config, update):
        """Procesa un update de Telegram"""
        try:
            # Verificar si es un mensaje
            if "message" not in update:
                return

            message = update["message"]

            # Verificar si es un comando
            if "text" not in message or not message["text"].startswith("/"):
                return

            command = message["text"].split()[0].lower()
            chat = message.get("chat", {})
            chat_id = chat.get("id")
            chat_type = chat.get("type")
            chat_title = chat.get("title", "Chat Privado")
            user = message.get("from", {})
            username = user.get("username", "Unknown")
            first_name = user.get("first_name", "Usuario")

            # Procesar comando /get_chat_id
            if command == "/get_chat_id":
                self.stdout.write(
                    self.style.SUCCESS(
                        f"📱 Comando /get_chat_id recibido de @{username} en '{chat_title}' (ID: {chat_id})"
                    )
                )

                # Preparar respuesta
                if chat_type in ["group", "supergroup"]:
                    response_message = f"""
🆔 <b>Información del Chat</b>

<b>📛 Nombre:</b> {chat_title}
<b>🔢 Chat ID:</b> <code>{chat_id}</code>
<b>📱 Tipo:</b> {chat_type.capitalize()}

<b>✅ ¿Cómo usar este ID?</b>

1️⃣ Copia el Chat ID de arriba
2️⃣ Ve al panel de administración de tu empresa
3️⃣ En la sección "Chats de Telegram", haz clic en "Agregar"
4️⃣ Pega el Chat ID y guarda

¡Listo! Empezarás a recibir notificaciones automáticamente.
                    """
                else:
                    response_message = f"""
🆔 <b>Información del Chat</b>

<b>👤 Usuario:</b> {first_name} (@{username})
<b>🔢 Chat ID:</b> <code>{chat_id}</code>
<b>📱 Tipo:</b> Chat Privado

⚠️ <b>Nota:</b> Este es un chat privado. Para recibir notificaciones de tu empresa, debes:

1️⃣ Crear un <b>grupo</b> en Telegram
2️⃣ Agregar este bot al grupo
3️⃣ Enviar /get_chat_id en el <b>grupo</b>
4️⃣ Usar el Chat ID del grupo en el panel de administración

Los chats privados no son recomendados para notificaciones empresariales.
                    """

                # Enviar respuesta
                self._send_message(config, chat_id, response_message)

            elif command == "/start":
                self.stdout.write(
                    self.style.SUCCESS(
                        f"👋 Comando /start recibido de @{username}"
                    )
                )

                welcome_message = f"""
👋 <b>¡Bienvenido!</b>

Soy el bot de notificaciones de tu empresa.

<b>🔧 Comandos disponibles:</b>

/get_chat_id - Obtener el ID de este chat
/start - Ver este mensaje de bienvenida
/help - Ayuda sobre cómo configurar

<b>💡 ¿Cómo empezar?</b>

1️⃣ Agrega este bot a un grupo de Telegram
2️⃣ Envía /get_chat_id en el grupo
3️⃣ Copia el Chat ID que te respondo
4️⃣ Configúralo en el panel de administración

¡Es así de fácil! 🚀
                """

                self._send_message(config, chat_id, welcome_message)

            elif command == "/help":
                self.stdout.write(
                    self.style.SUCCESS(f"❓ Comando /help recibido de @{username}")
                )

                help_message = f"""
ℹ️ <b>Ayuda - Bot de Notificaciones</b>

<b>¿Qué hace este bot?</b>
Envía notificaciones automáticas cuando llegan emails importantes a tu empresa.

<b>¿Cómo configurarlo?</b>

<b>Paso 1:</b> Crear o seleccionar un grupo
• Crea un nuevo grupo en Telegram
• O usa un grupo existente
• Agrega este bot al grupo

<b>Paso 2:</b> Obtener el Chat ID
• En el grupo, envía: /get_chat_id
• El bot responderá con el ID numérico

<b>Paso 3:</b> Configurar en el panel
• Accede al panel de administración de tu empresa
• Ve a "Chats de Telegram"
• Agrega el Chat ID que obtuviste

<b>Paso 4:</b> ¡Listo!
• El bot empezará a enviar notificaciones automáticamente
• Recibirás alertas de emails importantes

<b>🔧 Comandos:</b>
/get_chat_id - Obtener ID del chat
/start - Mensaje de bienvenida
/help - Esta ayuda

¿Problemas? Contacta al administrador del sistema.
                """

                self._send_message(config, chat_id, help_message)

            else:
                # Comando desconocido
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  Comando desconocido '{command}' de @{username}"
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error procesando update: {str(e)}")
            )
            logger.error(f"Error procesando update: {str(e)}", exc_info=True)

    def _send_message(self, config, chat_id, text):
        """Envía un mensaje a través del bot"""
        try:
            url = f"https://api.telegram.org/bot{config.bot_token}/sendMessage"
            data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

            response = requests.post(url, data=data, timeout=10)

            if response.status_code == 200:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Mensaje enviado a chat {chat_id}")
                )
                return True
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ Error enviando mensaje: {response.text}"
                    )
                )
                return False

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error enviando mensaje: {str(e)}")
            )
            return False
