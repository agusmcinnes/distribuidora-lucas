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
                "💡 Nuevo: Los usuarios pueden registrarse con /register CODIGO"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "📋 Alternativa: /get_chat_id para obtener el Chat ID (método manual)"
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
<b>📱 Tipo:</b> Grupo

<b>✅ ¿Cómo usar este ID?</b>

<b>Método Recomendado (con código):</b>
1️⃣ Solicita un código de registro al administrador
2️⃣ Envía: <code>/register CODIGO</code>
3️⃣ ¡Listo! Registro automático

<b>Método Alternativo (manual):</b>
1️⃣ Copia el Chat ID de arriba
2️⃣ Comparte el ID con el administrador
3️⃣ Espera a que configure el chat manualmente
                    """
                else:
                    response_message = f"""
🆔 <b>Información del Chat</b>

<b>👤 Usuario:</b> {first_name} (@{username})
<b>🔢 Chat ID:</b> <code>{chat_id}</code>
<b>📱 Tipo:</b> Chat Privado

<b>✅ ¿Cómo usar este ID?</b>

<b>Método Recomendado (con código):</b>
1️⃣ Solicita un código de registro al administrador
2️⃣ Envía: <code>/register CODIGO</code>
3️⃣ ¡Listo! Registro automático

<b>Método Alternativo (manual):</b>
1️⃣ Copia el Chat ID de arriba
2️⃣ Comparte el ID con el administrador
3️⃣ Espera a que configure el chat manualmente

💡 <b>Tip:</b> Los chats privados son perfectos para notificaciones personales. Si necesitas compartir con un equipo, usa un grupo.
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

/register CODIGO - Registrar este chat con un código
/get_chat_id - Obtener el ID de este chat
/start - Ver este mensaje de bienvenida
/help - Ayuda sobre cómo configurar

<b>💡 ¿Cómo empezar? (Método Recomendado)</b>

1️⃣ Solicita un código de registro al administrador
2️⃣ Envía: <code>/register CODIGO</code>
3️⃣ ¡Listo! Comenzarás a recibir notificaciones automáticamente

<b>📋 Método Alternativo:</b>

1️⃣ Envía /get_chat_id para obtener el ID del chat
2️⃣ Comparte el ID con el administrador para configuración manual

<b>📱 Tipos de chat soportados:</b>

• <b>Chats privados:</b> Para notificaciones personales
• <b>Grupos:</b> Para compartir notificaciones con tu equipo

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

<b>🎫 MÉTODO RECOMENDADO - Registro con Código:</b>

<b>Paso 1:</b> Obtén un código
• Solicita un código de registro al administrador de tu empresa
• El código tiene formato: ABC12345

<b>Paso 2:</b> Registra tu chat
• Puedes usar un <b>chat privado</b> (solo para ti) o un <b>grupo</b> (para compartir con tu equipo)
• Si es grupo, agrega este bot al grupo primero
• Envía: <code>/register CODIGO</code>
• Ejemplo: <code>/register ABC12345</code>

<b>Paso 3:</b> ¡Listo!
• El bot confirmará el registro
• Comenzarás a recibir notificaciones automáticamente

<b>📋 MÉTODO ALTERNATIVO - Configuración Manual:</b>

Si prefieres el método tradicional:
• Envía /get_chat_id para obtener tu Chat ID
• Comparte el ID con el administrador
• El administrador configurará el chat manualmente

<b>📱 Tipos de chat:</b>
• <b>Chat privado:</b> Perfecto para notificaciones personales
• <b>Grupo:</b> Ideal para compartir con tu equipo

<b>🔧 Comandos disponibles:</b>
/register CODIGO - Registrar con código
/get_chat_id - Obtener ID del chat
/start - Mensaje de bienvenida
/help - Esta ayuda

¿Problemas? Contacta al administrador del sistema.
                """

                self._send_message(config, chat_id, help_message)

            elif command == "/register":
                self.stdout.write(
                    self.style.SUCCESS(
                        f"🎫 Comando /register recibido de @{username} en '{chat_title}' (ID: {chat_id})"
                    )
                )

                # Extraer el código del mensaje
                parts = message["text"].split()
                if len(parts) < 2:
                    error_message = """
❌ <b>Error: Falta el código de registro</b>

<b>Uso correcto:</b>
/register CODIGO

<b>Ejemplo:</b>
/register ABC12345

<b>¿No tienes un código?</b>
Solicita un código de registro al administrador de tu empresa.
                    """
                    self._send_message(config, chat_id, error_message)
                    return

                code = parts[1].strip().upper()

                # Recopilar información del chat
                chat_data = {
                    'chat_id': chat_id,
                    'chat_type': chat_type,
                    'username': chat.get('username', ''),
                    'title': chat_title if chat_type in ['group', 'supergroup', 'channel'] else '',
                }

                # Intentar registrar
                from telegram_bot.services import TelegramRegistrationService
                result = TelegramRegistrationService.register_chat_with_code(code, chat_data)

                if result['success']:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Chat {chat_id} registrado exitosamente con código {code}"
                        )
                    )
                    success_message = result['message']
                    self._send_message(config, chat_id, success_message)
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"❌ Error registrando chat {chat_id}: {result.get('error_code', 'UNKNOWN')}"
                        )
                    )
                    error_message = result['message']
                    self._send_message(config, chat_id, error_message)

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
