"""
Sistema de procesamiento automático de emails sin Redis
Usando APScheduler para Windows
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import time
import threading
from datetime import datetime
import logging

logger = logging.getLogger("imap_handler")


class Command(BaseCommand):
    help = "Inicia procesamiento automático de emails sin Redis"

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=300,  # 5 minutos
            help="Intervalo en segundos entre procesamientos",
        )
        parser.add_argument(
            "--daemon",
            action="store_true",
            help="Ejecutar como daemon en segundo plano",
        )

    def handle(self, *args, **options):
        interval = options["interval"]

        self.stdout.write(
            self.style.SUCCESS(
                f"\n🚀 DISTRIBUIDORA LUCAS - PROCESADOR AUTOMÁTICO\n"
                f"{'='*50}\n"
                f"⏰ Intervalo: {interval} segundos ({interval/60:.1f} minutos)\n"
                f"📧 Email: {settings.IMAP_EMAIL}\n"
                f"🏠 Host: {settings.IMAP_HOST}\n"
                f"📦 Lote: {settings.IMAP_BATCH_SIZE} emails\n"
                f"\n🔄 Procesando cada {interval/60:.1f} minutos...\n"
                f"Presiona Ctrl+C para detener\n"
            )
        )

        try:
            self._run_scheduler(interval)
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.SUCCESS("\n🛑 Procesador detenido por el usuario")
            )

    def _run_scheduler(self, interval):
        """Ejecuta el procesador en un bucle"""
        last_run = 0

        while True:
            current_time = time.time()

            # Si ha pasado el tiempo necesario, procesar
            if current_time - last_run >= interval:
                self._process_emails()
                last_run = current_time

            # Dormir 10 segundos antes de verificar de nuevo
            time.sleep(10)

    def _process_emails(self):
        """Procesa los emails"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.stdout.write(f"\n🔄 [{timestamp}] Procesando emails...")

            from imap_handler.services import IMAPService
            from imap_handler.models import IMAPConfiguration
            from company.models import Company

            # Crear/actualizar configuración desde .env
            company, _ = Company.objects.get_or_create(
                name="Distribuidora Lucas", defaults={"is_active": True}
            )

            config, created = IMAPConfiguration.objects.get_or_create(
                name="Gmail Distribuidora",
                defaults={
                    "company": company,
                    "host": settings.IMAP_HOST,
                    "port": settings.IMAP_PORT,
                    "username": settings.IMAP_EMAIL,
                    "password": settings.IMAP_PASSWORD,
                    "use_ssl": settings.IMAP_USE_SSL,
                    "inbox_folder": settings.IMAP_FOLDER_INBOX,
                    "processed_folder": settings.IMAP_FOLDER_PROCESSED,
                    "is_active": True,
                    "max_emails_per_check": settings.IMAP_BATCH_SIZE,
                },
            )

            if not created:
                # Actualizar configuración con valores actuales del .env
                config.host = settings.IMAP_HOST
                config.port = settings.IMAP_PORT
                config.username = settings.IMAP_EMAIL
                config.password = settings.IMAP_PASSWORD
                config.use_ssl = settings.IMAP_USE_SSL
                config.inbox_folder = settings.IMAP_FOLDER_INBOX
                config.processed_folder = settings.IMAP_FOLDER_PROCESSED
                config.max_emails_per_check = settings.IMAP_BATCH_SIZE
                config.save()

            # Procesar emails
            service = IMAPService()
            result = service.process_emails_for_config(config)

            if result.get("status") == "success":
                processed = result.get("processed", 0)
                failed = result.get("failed", 0)

                if processed > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ [{timestamp}] Procesados: {processed}, Fallidos: {failed}"
                        )
                    )
                else:
                    self.stdout.write(f"📭 [{timestamp}] No hay emails nuevos")
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ [{timestamp}] Error: {result.get('message', 'Desconocido')}"
                    )
                )

        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.stdout.write(
                self.style.ERROR(f"❌ [{timestamp}] Error procesando: {str(e)}")
            )
            logger.error(f"Error en procesamiento automático: {str(e)}", exc_info=True)
