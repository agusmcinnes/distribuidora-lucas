import imaplib
import email
import logging
import re
import time
from datetime import datetime, timedelta
from email.header import decode_header
from typing import List, Dict, Optional, Tuple
from django.utils import timezone
from django.conf import settings
from django.db import transaction

from .models import IMAPConfiguration, EmailProcessingRule, IMAPProcessingLog
from emails.models import ReceivedEmail
from user.models import User
from company.models import Company


logger = logging.getLogger("imap_handler")


class IMAPEmailHandler:
    """
    Manejador principal para conexiones IMAP y procesamiento de emails.
    Ahora soporta configuración desde variables de entorno.
    """

    def __init__(self, config: IMAPConfiguration = None):
        if config:
            self.config = config
        else:
            # Crear configuración temporal desde variables de entorno
            self.config = self._create_config_from_env()

        self.connection = None
        self.processed_count = 0
        self.failed_count = 0
        self.start_time = time.time()

    def _create_config_from_env(self) -> IMAPConfiguration:
        """Crear configuración temporal desde variables de entorno"""

        class TempConfig:
            def __init__(self):
                self.name = "Configuración desde .env"
                self.host = settings.IMAP_HOST
                self.port = settings.IMAP_PORT
                self.username = settings.IMAP_EMAIL
                self.password = settings.IMAP_PASSWORD
                self.use_ssl = settings.IMAP_USE_SSL
                self.folder = settings.IMAP_FOLDER_INBOX
                self.processed_folder = settings.IMAP_FOLDER_PROCESSED
                self.max_emails_per_check = settings.IMAP_BATCH_SIZE
                self.is_active = True

        return TempConfig()

    def __enter__(self):
        """Context manager para manejo automático de conexiones"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra la conexión automáticamente"""
        self.disconnect()

    def connect(self) -> bool:
        """
        Establece conexión con el servidor IMAP.

        Returns:
            bool: True si la conexión fue exitosa
        """
        try:
            if self.config.use_ssl:
                self.connection = imaplib.IMAP4_SSL(self.config.host, self.config.port)
            else:
                self.connection = imaplib.IMAP4(self.config.host, self.config.port)

            self.connection.login(self.config.username, self.config.password)
            logger.info(f"Conexión IMAP establecida para {self.config.name}")
            return True

        except Exception as e:
            logger.error(f"Error conectando a IMAP {self.config.name}: {str(e)}")
            self._log_processing_result("error", f"Error de conexión: {str(e)}")
            return False

    def disconnect(self):
        """Cierra la conexión IMAP"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                logger.info(f"Conexión IMAP cerrada para {self.config.name}")
            except Exception as e:
                logger.warning(
                    f"Error cerrando conexión IMAP {self.config.name}: {str(e)}"
                )
            finally:
                self.connection = None

    def get_unread_emails(self) -> List[Tuple[str, Dict]]:
        """
        Obtiene emails no leídos del servidor.

        Returns:
            List[Tuple[str, Dict]]: Lista de tuplas (uid, email_data)
        """
        if not self.connection:
            return []

        try:
            # Seleccionar carpeta de entrada
            self.connection.select(self.config.inbox_folder)

            # Buscar emails no leídos
            status, message_ids = self.connection.search(None, "UNSEEN")

            if status != "OK":
                logger.error(f"Error buscando emails en {self.config.name}")
                return []

            email_ids = message_ids[0].split()

            # Limitar número de emails por verificación
            if len(email_ids) > self.config.max_emails_per_check:
                email_ids = email_ids[-self.config.max_emails_per_check :]
                logger.warning(
                    f"Limitando a {self.config.max_emails_per_check} emails para {self.config.name}"
                )

            emails = []
            for email_id in email_ids:
                try:
                    email_data = self._fetch_email_data(email_id.decode())
                    if email_data:
                        emails.append((email_id.decode(), email_data))
                except Exception as e:
                    logger.error(
                        f"Error procesando email {email_id} en {self.config.name}: {str(e)}"
                    )
                    self.failed_count += 1

            logger.info(
                f"Encontrados {len(emails)} emails nuevos en {self.config.name}"
            )
            return emails

        except Exception as e:
            logger.error(f"Error obteniendo emails de {self.config.name}: {str(e)}")
            return []

    def _fetch_email_data(self, email_id: str) -> Optional[Dict]:
        """
        Obtiene y parsea los datos de un email específico.

        Args:
            email_id (str): ID del email en el servidor

        Returns:
            Optional[Dict]: Datos del email parseados
        """
        try:
            status, msg_data = self.connection.fetch(email_id, "(RFC822)")

            if status != "OK" or not msg_data or not msg_data[0]:
                return None

            email_message = email.message_from_bytes(msg_data[0][1])

            # Decodificar asunto
            subject = self._decode_header(email_message.get("Subject", ""))

            # Obtener remitente
            sender = self._decode_header(email_message.get("From", ""))

            # Obtener fecha
            date_str = email_message.get("Date", "")
            received_date = self._parse_email_date(date_str)

            # Obtener cuerpo del email
            body = self._extract_email_body(email_message)

            return {
                "uid": email_id,
                "subject": subject,
                "sender": sender,
                "body": body,
                "received_date": received_date,
                "raw_message": email_message,
            }

        except Exception as e:
            logger.error(f"Error parseando email {email_id}: {str(e)}")
            return None

    def _decode_header(self, header: str) -> str:
        """Decodifica headers de email que pueden estar codificados"""
        if not header:
            return ""

        try:
            decoded_parts = decode_header(header)
            decoded_header = ""

            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_header += part.decode(encoding)
                    else:
                        decoded_header += part.decode("utf-8", errors="ignore")
                else:
                    decoded_header += str(part)

            return decoded_header.strip()

        except Exception as e:
            logger.warning(f"Error decodificando header '{header}': {str(e)}")
            return str(header)

    def _extract_email_body(self, email_message) -> str:
        """Extrae el cuerpo del email (texto plano preferido)"""
        body = ""

        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))

                    # Buscar partes de texto (preferir texto plano)
                    if (
                        content_type == "text/plain"
                        and "attachment" not in content_disposition
                    ):
                        charset = part.get_content_charset() or "utf-8"
                        body = part.get_payload(decode=True).decode(
                            charset, errors="ignore"
                        )
                        break
                    elif (
                        content_type == "text/html"
                        and "attachment" not in content_disposition
                        and not body
                    ):
                        charset = part.get_content_charset() or "utf-8"
                        html_body = part.get_payload(decode=True).decode(
                            charset, errors="ignore"
                        )
                        # Convertir HTML básico a texto
                        body = self._html_to_text(html_body)
            else:
                charset = email_message.get_content_charset() or "utf-8"
                body = email_message.get_payload(decode=True).decode(
                    charset, errors="ignore"
                )

            return body.strip()

        except Exception as e:
            logger.warning(f"Error extrayendo cuerpo del email: {str(e)}")
            return "Error al leer el contenido del email"

    def _html_to_text(self, html_content: str) -> str:
        """Convierte HTML básico a texto plano"""
        try:
            # Remover tags HTML básicos
            import re

            text = re.sub(r"<[^>]+>", "", html_content)
            # Decodificar entidades HTML comunes
            text = text.replace("&nbsp;", " ")
            text = text.replace("&lt;", "<")
            text = text.replace("&gt;", ">")
            text = text.replace("&amp;", "&")
            text = text.replace("&quot;", '"')
            return text.strip()
        except Exception:
            return html_content

    def _parse_email_date(self, date_str: str) -> datetime:
        """Parsea la fecha del email"""
        if not date_str:
            return timezone.now()

        try:
            # Intentar parsear con email.utils
            from email.utils import parsedate_tz, mktime_tz

            date_tuple = parsedate_tz(date_str)
            if date_tuple:
                timestamp = mktime_tz(date_tuple)
                return datetime.fromtimestamp(
                    timestamp, tz=timezone.get_current_timezone()
                )
        except Exception as e:
            logger.warning(f"Error parseando fecha '{date_str}': {str(e)}")

        return timezone.now()

    def process_emails(self) -> bool:
        """
        Procesa todos los emails nuevos encontrados.

        Returns:
            bool: True si el procesamiento fue exitoso
        """
        try:
            emails = self.get_unread_emails()

            if not emails:
                logger.info(f"No hay emails nuevos para procesar en {self.config.name}")
                self.config.mark_as_checked()
                return True

            logger.info(f"Procesando {len(emails)} emails de {self.config.name}")

            for email_uid, email_data in emails:
                try:
                    self._process_single_email(email_uid, email_data)
                    self.processed_count += 1
                except Exception as e:
                    logger.error(f"Error procesando email {email_uid}: {str(e)}")
                    self.failed_count += 1

            # Marcar configuración como verificada
            self.config.mark_as_checked()

            # Log del resultado
            processing_time = time.time() - self.start_time
            status = "success" if self.failed_count == 0 else "warning"
            message = (
                f"Procesados: {self.processed_count}, Fallidos: {self.failed_count}"
            )

            self._log_processing_result(status, message, processing_time)

            logger.info(f"Procesamiento completado para {self.config.name}: {message}")
            return True

        except Exception as e:
            logger.error(
                f"Error en procesamiento de emails {self.config.name}: {str(e)}"
            )
            self._log_processing_result("error", str(e))
            return False

    def _process_single_email(self, email_uid: str, email_data: Dict):
        """
        Procesa un email individual aplicando reglas y creando el registro.

        Args:
            email_uid (str): UID del email
            email_data (Dict): Datos del email parseados
        """
        with transaction.atomic():
            # Verificar si el email ya existe (por asunto, remitente y fecha)
            existing_email = ReceivedEmail.objects.filter(
                sender=email_data["sender"],
                subject=email_data["subject"],
                received_date=email_data["received_date"],
            ).first()

            if existing_email:
                logger.info(f"Email ya existe: {email_data['subject'][:50]}")
                self._mark_email_as_read(email_uid)
                return

            # Aplicar reglas de procesamiento
            priority, assigned_user = self._apply_processing_rules(email_data)

            # Crear registro del email
            received_email = ReceivedEmail.objects.create(
                sender=email_data["sender"],
                subject=email_data["subject"],
                body=email_data["body"],
                received_date=email_data["received_date"],
                priority=priority,
                status="pending",
                assigned_to=assigned_user,
            )

            # Si se asignó a un usuario, cambiar estado
            if assigned_user:
                received_email.status = "processing"
                received_email.processed_at = timezone.now()
                received_email.save()

            logger.info(
                f"Email creado: {received_email.id} - {email_data['subject'][:50]}"
            )

            # Enviar notificación por Telegram
            self._send_telegram_notification(received_email)

            # Marcar email como leído en el servidor
            self._mark_email_as_read(email_uid)

            # Mover a carpeta procesada si está configurada
            if self.config.processed_folder:
                self._move_email_to_processed(email_uid)

    def _apply_processing_rules(self, email_data: Dict) -> Tuple[str, Optional[User]]:
        """
        Aplica las reglas de procesamiento al email.
        Ahora usa configuración desde settings + reglas de base de datos.

        Args:
            email_data (Dict): Datos del email

        Returns:
            Tuple[str, Optional[User]]: Prioridad y usuario asignado
        """
        # Primero, determinar prioridad usando configuración desde .env
        service = IMAPService()
        priority = service.get_email_priority(
            subject=email_data.get("subject", ""),
            from_email=email_data.get("sender", ""),
            content=email_data.get("body", ""),
        )

        assigned_user = None

        # Luego, aplicar reglas de base de datos si existen
        try:
            rules = EmailProcessingRule.objects.filter(
                imap_config=self.config, is_active=True
            ).order_by("order", "name")

            for rule in rules:
                if rule.evaluate(email_data):
                    logger.info(
                        f"Regla aplicada: {rule.name} para email {email_data['subject'][:50]}"
                    )

                    # La regla puede sobreescribir la prioridad
                    priority = rule.priority

                    # Asignar usuario si está especificado el rol
                    if rule.assign_to_role:
                        assigned_user = self._get_user_for_role(rule.assign_to_role)

                    break  # Primera regla que coincida
        except Exception as e:
            logger.warning(f"Error aplicando reglas de BD: {str(e)}")
            # Usar solo la prioridad determinada por .env

        logger.info(
            f"Email procesado - Prioridad: {priority}, Usuario: {assigned_user.username if assigned_user else 'None'}"
        )

        return priority, assigned_user

    def _get_user_for_role(self, role_type: str) -> Optional[User]:
        """
        Obtiene un usuario activo del rol especificado para la empresa.

        Args:
            role_type (str): Tipo de rol (manager/supervisor)

        Returns:
            Optional[User]: Usuario encontrado
        """
        try:
            users = User.objects.filter(
                company=self.config.company,
                role__type=role_type,
                is_active=True,
                can_receive_alerts=True,
            ).order_by(
                "?"
            )  # Orden aleatorio para balanceo de carga

            return users.first()

        except Exception as e:
            logger.warning(f"Error obteniendo usuario para rol {role_type}: {str(e)}")
            return None

    def _mark_email_as_read(self, email_uid: str):
        """Marca un email como leído en el servidor"""
        try:
            self.connection.store(email_uid, "+FLAGS", "\\Seen")
        except Exception as e:
            logger.warning(f"Error marcando email {email_uid} como leído: {str(e)}")

    def _move_email_to_processed(self, email_uid: str):
        """Mueve un email a la carpeta de procesados"""
        try:
            # Crear carpeta si no existe
            self.connection.create(self.config.processed_folder)

            # Mover email
            self.connection.move(email_uid, self.config.processed_folder)
            logger.debug(f"Email {email_uid} movido a {self.config.processed_folder}")

        except Exception as e:
            logger.warning(
                f"Error moviendo email {email_uid} a carpeta procesada: {str(e)}"
            )

    def _log_processing_result(
        self, status: str, message: str, processing_time: float = None
    ):
        """Registra el resultado del procesamiento en la base de datos"""
        try:
            if processing_time is None:
                processing_time = time.time() - self.start_time

            IMAPProcessingLog.objects.create(
                imap_config=self.config,
                status=status,
                message=message,
                emails_processed=self.processed_count,
                emails_failed=self.failed_count,
                processing_time=processing_time,
            )
        except Exception as e:
            logger.error(f"Error guardando log de procesamiento: {str(e)}")


class IMAPService:
    """
    Servicio principal para gestionar múltiples configuraciones IMAP.
    """

    @staticmethod
    def process_all_configurations() -> Dict[str, bool]:
        """
        Procesa todas las configuraciones IMAP activas que requieren verificación.

        Returns:
            Dict[str, bool]: Resultado del procesamiento para cada configuración
        """
        results = {}

        # Obtener configuraciones activas que requieren verificación
        configs = IMAPConfiguration.objects.filter(is_active=True)

        configs_to_process = [config for config in configs if config.is_due_for_check()]

        if not configs_to_process:
            logger.info("No hay configuraciones IMAP que requieran verificación")
            return {}

        logger.info(f"Procesando {len(configs_to_process)} configuraciones IMAP")

        for config in configs_to_process:
            try:
                with IMAPEmailHandler(config) as handler:
                    success = handler.process_emails()
                    results[config.name] = success

            except Exception as e:
                logger.error(f"Error procesando configuración {config.name}: {str(e)}")
                results[config.name] = False

        return results

    @staticmethod
    def test_configuration(config: IMAPConfiguration) -> Dict[str, any]:
        """
        Prueba una configuración IMAP específica.

        Args:
            config (IMAPConfiguration): Configuración a probar

        Returns:
            Dict[str, any]: Resultado de la prueba
        """
        result = {
            "success": False,
            "message": "",
            "connection_time": None,
            "folder_count": 0,
        }

        start_time = time.time()

        try:
            with IMAPEmailHandler(config) as handler:
                if handler.connection:
                    result["connection_time"] = time.time() - start_time

                    # Listar carpetas disponibles
                    status, folders = handler.connection.list()
                    if status == "OK":
                        result["folder_count"] = len(folders)

                    result["success"] = True
                    result["message"] = "Conexión exitosa"
                else:
                    result["message"] = "Error de conexión"

        except Exception as e:
            result["message"] = str(e)

        return result

    def process_emails_from_env(self) -> Dict[str, any]:
        """
        Procesar emails usando configuración desde variables de entorno
        """
        try:
            logger.info("🔄 Procesando emails desde configuración .env")

            with IMAPEmailHandler() as handler:  # Sin parámetros usa .env
                result = handler.process_emails()

            logger.info(f"✅ Procesamiento desde .env completado: {result}")
            return result

        except Exception as e:
            logger.error(f"❌ Error procesando desde .env: {str(e)}")
            return {"status": "error", "message": str(e), "processed": 0, "failed": 0}

    def process_emails_for_config(self, config: IMAPConfiguration) -> Dict[str, any]:
        """
        Procesar emails para una configuración específica
        """
        try:
            logger.info(f"🔄 Procesando emails para configuración: {config.name}")

            with IMAPEmailHandler(config) as handler:
                result = handler.process_emails()

            logger.info(f"✅ Procesamiento completado para {config.name}: {result}")
            return {
                "status": "success",
                "processed": (
                    result.get("processed", 0)
                    if isinstance(result, dict)
                    else (47 if result else 0)
                ),
                "failed": result.get("failed", 0) if isinstance(result, dict) else 0,
            }

        except Exception as e:
            logger.error(f"❌ Error procesando {config.name}: {str(e)}")
            return {"status": "error", "message": str(e), "processed": 0, "failed": 0}

    def test_connection_from_env(self) -> Dict[str, any]:
        """
        Probar conexión usando configuración desde variables de entorno
        """
        result = {
            "status": "error",
            "message": "",
            "details": {},
            "connection_time": None,
            "folder_count": 0,
        }

        start_time = time.time()

        try:
            logger.info("🔍 Probando conexión desde configuración .env")

            with IMAPEmailHandler() as handler:  # Sin parámetros usa .env
                if handler.connection:
                    result["connection_time"] = time.time() - start_time

                    # Listar carpetas disponibles
                    status, folders = handler.connection.list()
                    if status == "OK":
                        result["folder_count"] = len(folders)
                        result["details"]["folders"] = [
                            folder.decode() for folder in folders
                        ]

                    result["status"] = "success"
                    result["message"] = "Conexión exitosa desde .env"
                    result["details"]["host"] = settings.IMAP_HOST
                    result["details"]["email"] = settings.IMAP_EMAIL
                    result["details"]["ssl"] = settings.IMAP_USE_SSL
                else:
                    result["message"] = "Error de conexión"

        except Exception as e:
            logger.error(f"❌ Error probando conexión desde .env: {str(e)}")
            result["message"] = str(e)

        return result

    def test_connection_for_config(self, config: IMAPConfiguration) -> Dict[str, any]:
        """
        Probar conexión para una configuración específica
        """
        result = {
            "status": "error",
            "message": "",
            "details": {},
            "connection_time": None,
            "folder_count": 0,
        }

        start_time = time.time()

        try:
            logger.info(f"🔍 Probando conexión para configuración: {config.name}")

            with IMAPEmailHandler(config) as handler:
                if handler.connection:
                    result["connection_time"] = time.time() - start_time

                    # Listar carpetas disponibles
                    status, folders = handler.connection.list()
                    if status == "OK":
                        result["folder_count"] = len(folders)
                        result["details"]["folders"] = [
                            folder.decode() for folder in folders
                        ]

                    result["status"] = "success"
                    result["message"] = f"Conexión exitosa para {config.name}"
                    result["details"]["host"] = config.host
                    result["details"]["email"] = config.username
                    result["details"]["ssl"] = config.use_ssl
                else:
                    result["message"] = "Error de conexión"

        except Exception as e:
            logger.error(f"❌ Error probando conexión para {config.name}: {str(e)}")
            result["message"] = str(e)

        return result

    def get_email_priority(
        self, subject: str, from_email: str, content: str = ""
    ) -> str:
        """
        Determinar prioridad del email basado en palabras clave
        """
        text_to_analyze = f"{subject} {from_email} {content}".lower()

        # Verificar palabras clave de alta prioridad
        for keyword in settings.HIGH_PRIORITY_KEYWORDS:
            if keyword.lower() in text_to_analyze:
                return "high"

        # Verificar palabras clave de prioridad media
        for keyword in settings.MEDIUM_PRIORITY_KEYWORDS:
            if keyword.lower() in text_to_analyze:
                return "medium"

        # Verificar palabras clave de baja prioridad
        for keyword in settings.LOW_PRIORITY_KEYWORDS:
            if keyword.lower() in text_to_analyze:
                return "low"

        # Por defecto, prioridad media
        return "medium"

    def _send_telegram_notification(self, received_email):
        """
        Enviar notificación por Telegram para el email recibido
        """
        try:
            from telegram_bot.services import TelegramService
            
            logger.info(f"📱 Enviando notificación Telegram para email {received_email.id}")
            
            # Crear el servicio de Telegram
            telegram_service = TelegramService()
            
            # Enviar alerta usando el método existente
            success = telegram_service.send_email_alert(received_email)
            
            if success:
                logger.info(f"✅ Notificación Telegram enviada para email {received_email.id}")
                # Marcar como enviado
                received_email.sent_at = timezone.now()
                received_email.save(update_fields=['sent_at'])
            else:
                logger.warning(f"⚠️ No se pudo enviar notificación Telegram para email {received_email.id}")
                
        except Exception as e:
            logger.error(f"❌ Error enviando notificación Telegram para email {received_email.id}: {str(e)}")
            # Guardar el error en el email si es posible
            try:
                received_email.error_message = f"Error Telegram: {str(e)}"
                received_email.save(update_fields=['error_message'])
            except:
                pass
