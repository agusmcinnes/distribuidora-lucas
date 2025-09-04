from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from imap_handler.services import IMAPService
from imap_handler.models import IMAPConfiguration
import time


class Command(BaseCommand):
    help = "Procesa emails de todas las configuraciones IMAP activas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--config",
            type=str,
            help="Procesar solo una configuración específica por nombre",
        )
        parser.add_argument(
            "--daemon", action="store_true", help="Ejecutar como daemon (loop continuo)"
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=300,
            help="Intervalo en segundos para modo daemon (default: 300)",
        )
        parser.add_argument(
            "--max-iterations",
            type=int,
            default=0,
            help="Número máximo de iteraciones en modo daemon (0 = infinito)",
        )

    def handle(self, *args, **options):
        config_name = options.get("config")
        daemon_mode = options.get("daemon", False)
        interval = options.get("interval", 300)
        max_iterations = options.get("max_iterations", 0)

        if daemon_mode:
            self._run_daemon_mode(config_name, interval, max_iterations)
        else:
            self._run_single_execution(config_name)

    def _run_single_execution(self, config_name=None):
        """Ejecuta una sola verificación de emails"""
        self.stdout.write(
            self.style.SUCCESS(f"🚀 Iniciando procesamiento IMAP - {timezone.now()}")
        )

        try:
            if config_name:
                # Procesar configuración específica
                try:
                    config = IMAPConfiguration.objects.get(
                        name=config_name, is_active=True
                    )
                    results = {config_name: self._process_single_config(config)}
                except IMAPConfiguration.DoesNotExist:
                    raise CommandError(
                        f'Configuración IMAP "{config_name}" no encontrada o inactiva'
                    )
            else:
                # Procesar todas las configuraciones
                results = IMAPService.process_all_configurations()

            # Mostrar resultados
            self._display_results(results)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error durante el procesamiento: {str(e)}")
            )
            raise CommandError(str(e))

    def _run_daemon_mode(self, config_name, interval, max_iterations):
        """Ejecuta en modo daemon con loop continuo"""
        self.stdout.write(
            self.style.SUCCESS(f"🔄 Iniciando modo daemon - Intervalo: {interval}s")
        )

        if max_iterations > 0:
            self.stdout.write(f"📊 Máximo {max_iterations} iteraciones")

        iteration = 0

        try:
            while True:
                iteration += 1

                self.stdout.write(f"\n--- Iteración {iteration} - {timezone.now()} ---")

                try:
                    if config_name:
                        config = IMAPConfiguration.objects.get(
                            name=config_name, is_active=True
                        )
                        results = {config_name: self._process_single_config(config)}
                    else:
                        results = IMAPService.process_all_configurations()

                    self._display_results(results)

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"❌ Error en iteración {iteration}: {str(e)}")
                    )

                # Verificar si se alcanzó el máximo de iteraciones
                if max_iterations > 0 and iteration >= max_iterations:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Completadas {max_iterations} iteraciones"
                        )
                    )
                    break

                # Esperar antes de la siguiente iteración
                self.stdout.write(f"⏱️  Esperando {interval} segundos...")
                time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("\n🛑 Proceso interrumpido por el usuario")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\n❌ Error crítico en modo daemon: {str(e)}")
            )
            raise CommandError(str(e))

    def _process_single_config(self, config):
        """Procesa una configuración específica"""
        from imap_handler.services import IMAPEmailHandler

        try:
            with IMAPEmailHandler(config) as handler:
                return handler.process_emails()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error procesando {config.name}: {str(e)}")
            )
            return False

    def _display_results(self, results):
        """Muestra los resultados del procesamiento"""
        if not results:
            self.stdout.write(
                self.style.WARNING("⚠️  No hay configuraciones para procesar")
            )
            return

        self.stdout.write("\n📊 Resultados del procesamiento:")

        total_configs = len(results)
        successful_configs = sum(1 for success in results.values() if success)

        for config_name, success in results.items():
            status_icon = "✅" if success else "❌"
            status_color = self.style.SUCCESS if success else self.style.ERROR

            self.stdout.write(status_color(f"  {status_icon} {config_name}"))

        # Resumen final
        self.stdout.write(
            f"\n📋 Resumen: {successful_configs}/{total_configs} configuraciones procesadas exitosamente"
        )

        if successful_configs == total_configs:
            self.stdout.write(
                self.style.SUCCESS("🎉 ¡Todos los procesamientos exitosos!")
            )
        elif successful_configs > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  {total_configs - successful_configs} configuraciones fallaron"
                )
            )
        else:
            self.stdout.write(self.style.ERROR("❌ Todas las configuraciones fallaron"))
