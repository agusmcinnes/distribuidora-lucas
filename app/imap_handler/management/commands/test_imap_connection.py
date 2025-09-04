from django.core.management.base import BaseCommand, CommandError
from imap_handler.models import IMAPConfiguration
from imap_handler.services import IMAPService
import json


class Command(BaseCommand):
    help = "Prueba la conexión de una o todas las configuraciones IMAP"

    def add_arguments(self, parser):
        parser.add_argument(
            "config_name",
            nargs="?",
            type=str,
            help="Nombre de la configuración IMAP a probar (opcional, si no se especifica prueba todas)",
        )
        parser.add_argument(
            "--detailed",
            action="store_true",
            help="Mostrar información detallada de la prueba",
        )
        parser.add_argument(
            "--json", action="store_true", help="Mostrar resultado en formato JSON"
        )

    def handle(self, *args, **options):
        config_name = options.get("config_name")
        detailed = options.get("detailed", False)
        json_output = options.get("json", False)

        try:
            if config_name:
                # Probar configuración específica
                config = IMAPConfiguration.objects.get(name=config_name)
                result = {config_name: self._test_single_config(config, detailed)}
            else:
                # Probar todas las configuraciones
                configs = IMAPConfiguration.objects.filter(is_active=True)
                result = {}

                for config in configs:
                    result[config.name] = self._test_single_config(config, detailed)

        except IMAPConfiguration.DoesNotExist:
            raise CommandError(f'Configuración IMAP "{config_name}" no encontrada')

        if json_output:
            self.stdout.write(json.dumps(result, indent=2, default=str))
        else:
            self._display_results(result, detailed)

    def _test_single_config(self, config, detailed=False):
        """Prueba una configuración específica"""
        if not detailed:
            self.stdout.write(f"🔍 Probando configuración: {config.name}")

        test_result = IMAPService.test_configuration(config)

        if not detailed:
            if test_result["success"]:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {config.name}: Conexión exitosa")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ {config.name}: {test_result["message"]}')
                )

        return test_result

    def _display_results(self, results, detailed=False):
        """Muestra los resultados de las pruebas"""
        if not results:
            self.stdout.write(
                self.style.WARNING("⚠️  No hay configuraciones para probar")
            )
            return

        if detailed:
            self.stdout.write("\n📊 Resultados detallados de las pruebas:")
            self.stdout.write("=" * 60)

            for config_name, result in results.items():
                self.stdout.write(f"\n🔧 Configuración: {config_name}")
                self.stdout.write("-" * 40)

                if result["success"]:
                    self.stdout.write(self.style.SUCCESS("✅ Estado: EXITOSO"))

                    if result["connection_time"]:
                        self.stdout.write(
                            f'⏱️  Tiempo de conexión: {result["connection_time"]:.2f}s'
                        )

                    self.stdout.write(
                        f'📁 Carpetas encontradas: {result["folder_count"]}'
                    )

                else:
                    self.stdout.write(self.style.ERROR("❌ Estado: FALLIDO"))
                    self.stdout.write(f'🚨 Error: {result["message"]}')

        # Resumen final
        total_configs = len(results)
        successful_configs = sum(1 for result in results.values() if result["success"])

        self.stdout.write(
            f"\n📋 Resumen: {successful_configs}/{total_configs} configuraciones funcionando correctamente"
        )

        if successful_configs == total_configs:
            self.stdout.write(
                self.style.SUCCESS("🎉 ¡Todas las configuraciones están funcionando!")
            )
        elif successful_configs > 0:
            failed_configs = [
                name for name, result in results.items() if not result["success"]
            ]
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Configuraciones con problemas: {", ".join(failed_configs)}'
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR("❌ Ninguna configuración está funcionando")
            )
