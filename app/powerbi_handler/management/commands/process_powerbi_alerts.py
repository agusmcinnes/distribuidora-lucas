"""
Comando para procesar alertas de Power BI manualmente
"""

import json
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Procesa alertas desde Power BI manualmente"

    def add_arguments(self, parser):
        parser.add_argument(
            "--config-id",
            type=int,
            help="ID de la configuración de Power BI a usar",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simular procesamiento sin crear alertas",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Mostrar salida en formato JSON",
        )
        parser.add_argument(
            "--no-telegram",
            action="store_true",
            help="No enviar notificaciones a Telegram",
        )

    def handle(self, *args, **options):
        from powerbi_handler.models import PowerBIConfig
        from powerbi_handler.services import PowerBIAlertService, PowerBIQueryService

        self.stdout.write("=" * 60)
        self.stdout.write("Procesamiento de Alertas Power BI")
        self.stdout.write("=" * 60)

        # Obtener configuración
        if options["config_id"]:
            config = PowerBIConfig.objects.filter(id=options["config_id"]).first()
            if not config:
                raise CommandError(f"No se encontró configuración con ID {options['config_id']}")
        else:
            config = PowerBIConfig.objects.filter(is_active=True).first()

        if not config:
            raise CommandError(
                "No hay configuración de Power BI activa.\n"
                "Cree una desde el admin o proporcione un --config-id"
            )

        self.stdout.write(f"\nUsando configuración: {config.name}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("\n[MODO DRY-RUN] No se crearán alertas\n"))
            self._dry_run(config, options)
        else:
            self._process(config, options)

    def _dry_run(self, config, options):
        """Ejecuta en modo simulación"""
        from powerbi_handler.services import PowerBIQueryService
        from powerbi_handler.models import PowerBIAlert

        query_service = PowerBIQueryService(config)

        self.stdout.write("Ejecutando query DAX...")
        try:
            rows = query_service.execute_query()
            self.stdout.write(self.style.SUCCESS(f"  ✓ {len(rows)} registros obtenidos"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Error: {e}"))
            return

        # Verificar cuáles ya existen
        field_mapping = config.get_field_mapping()
        record_id_field = field_mapping.get("record_id", "id")

        record_ids = [str(row.get(record_id_field, "")) for row in rows if row.get(record_id_field)]
        existing_ids = set(
            PowerBIAlert.objects.filter(
                config=config,
                powerbi_record_id__in=record_ids,
            ).values_list("powerbi_record_id", flat=True)
        )

        new_count = sum(1 for row in rows if str(row.get(record_id_field, "")) not in existing_ids)
        existing_count = len(record_ids) - new_count

        self.stdout.write(f"\nResumen:")
        self.stdout.write(f"  - Registros totales: {len(rows)}")
        self.stdout.write(f"  - Ya procesados: {existing_count}")
        self.stdout.write(self.style.SUCCESS(f"  - Nuevos a procesar: {new_count}"))

        if new_count > 0 and rows:
            self.stdout.write("\nPrimeros registros nuevos:")
            count = 0
            for row in rows:
                if str(row.get(record_id_field, "")) not in existing_ids:
                    count += 1
                    if count > 5:
                        break
                    self.stdout.write(f"  [{count}] {json.dumps(row, default=str)[:150]}...")

    def _process(self, config, options):
        """Ejecuta el procesamiento real"""
        from powerbi_handler.services import PowerBIAlertService

        self.stdout.write("\nIniciando procesamiento...")

        try:
            service = PowerBIAlertService(config)

            # Si no queremos Telegram, monkey-patch el método
            if options["no_telegram"]:
                service._send_telegram_notification = lambda *args, **kwargs: None
                self.stdout.write(self.style.WARNING("  (Notificaciones Telegram desactivadas)"))

            result = service.process_alerts()

            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("Procesamiento completado"))
            self.stdout.write("=" * 60)

            self.stdout.write(f"\nResultados:")
            self.stdout.write(f"  - Registros obtenidos: {result.get('records_fetched', 0)}")
            self.stdout.write(f"  - Registros nuevos: {result.get('records_new', 0)}")
            self.stdout.write(f"  - Registros omitidos: {result.get('records_skipped', 0)}")
            self.stdout.write(
                self.style.SUCCESS(f"  - Alertas creadas: {result.get('alerts_created', 0)}")
            )
            if result.get("alerts_failed", 0) > 0:
                self.stdout.write(
                    self.style.ERROR(f"  - Alertas fallidas: {result.get('alerts_failed', 0)}")
                )

            if result.get("by_company"):
                self.stdout.write("\nPor empresa:")
                for company, count in result["by_company"].items():
                    self.stdout.write(f"  - {company}: {count} alertas")

            if options["json"]:
                self.stdout.write("\n" + json.dumps(result, default=str, indent=2))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nError en procesamiento: {e}"))
            raise CommandError(str(e))
