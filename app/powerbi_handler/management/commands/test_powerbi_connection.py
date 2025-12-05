"""
Comando para probar la conexión a Power BI
"""

import json
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = "Prueba la conexión a Power BI y muestra información del dataset"

    def add_arguments(self, parser):
        parser.add_argument(
            "--config-id",
            type=int,
            help="ID de la configuración de Power BI a probar",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Mostrar salida en formato JSON",
        )
        parser.add_argument(
            "--query",
            type=str,
            help="Query DAX personalizada para probar",
        )

    def handle(self, *args, **options):
        from powerbi_handler.models import PowerBIConfig
        from powerbi_handler.services import (
            PowerBIAuthService,
            PowerBIQueryService,
            test_powerbi_connection,
        )

        self.stdout.write("=" * 60)
        self.stdout.write("Test de Conexión Power BI")
        self.stdout.write("=" * 60)

        # Obtener configuración
        config = None
        if options["config_id"]:
            config = PowerBIConfig.objects.filter(id=options["config_id"]).first()
            if not config:
                raise CommandError(f"No se encontró configuración con ID {options['config_id']}")
        else:
            config = PowerBIConfig.objects.filter(is_active=True).first()

        if not config:
            self.stdout.write(self.style.WARNING(
                "\nNo hay configuración de Power BI. Creando una desde variables de entorno..."
            ))

            # Intentar crear desde settings
            if not all([
                getattr(settings, "POWERBI_TENANT_ID", ""),
                getattr(settings, "POWERBI_CLIENT_ID", ""),
                getattr(settings, "POWERBI_CLIENT_SECRET", ""),
            ]):
                raise CommandError(
                    "No hay configuración de Power BI ni variables de entorno configuradas.\n"
                    "Configure las variables POWERBI_* en .env o cree una configuración desde el admin."
                )

            config = PowerBIConfig(
                name="Desde ENV",
                tenant_id=getattr(settings, "POWERBI_TENANT_ID", ""),
                client_id=getattr(settings, "POWERBI_CLIENT_ID", ""),
                client_secret=getattr(settings, "POWERBI_CLIENT_SECRET", ""),
                group_id=getattr(settings, "POWERBI_GROUP_ID", ""),
                dataset_id=getattr(settings, "POWERBI_DATASET_ID", ""),
            )

        self.stdout.write(f"\nUsando configuración: {config.name}")
        self.stdout.write(f"Dataset ID: {config.dataset_id}")
        self.stdout.write(f"Group ID: {config.group_id}")

        # Test 1: Autenticación
        self.stdout.write("\n[1/3] Probando autenticación...")
        try:
            auth_service = PowerBIAuthService(config)
            token = auth_service.get_access_token()
            self.stdout.write(self.style.SUCCESS("  ✓ Autenticación exitosa"))
            self.stdout.write(f"    Token: {token[:20]}...{token[-10:]}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Error de autenticación: {e}"))
            if options["json"]:
                self.stdout.write(json.dumps({"success": False, "error": str(e)}))
            return

        # Test 2: Info del dataset
        self.stdout.write("\n[2/3] Obteniendo información del dataset...")
        try:
            query_service = PowerBIQueryService(config)
            dataset_info = query_service.get_dataset_info()

            if dataset_info:
                self.stdout.write(self.style.SUCCESS("  ✓ Dataset info obtenida"))
                self.stdout.write(f"    Nombre: {dataset_info.get('name', 'N/A')}")
                self.stdout.write(f"    Configurado por: {dataset_info.get('configuredBy', 'N/A')}")
                self.stdout.write(f"    Es refrescable: {dataset_info.get('isRefreshable', 'N/A')}")
            else:
                self.stdout.write(self.style.WARNING("  ! No se pudo obtener info del dataset"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  ! Error obteniendo info: {e}"))

        # Test 3: Query DAX
        self.stdout.write("\n[3/3] Ejecutando query DAX...")
        query = options.get("query") or config.dax_query or "EVALUATE ROW(\"Test\", 1)"

        try:
            rows = query_service.execute_query(query)
            self.stdout.write(self.style.SUCCESS(f"  ✓ Query exitosa: {len(rows)} registros"))

            if rows and len(rows) > 0:
                self.stdout.write("\n  Muestra de datos (primeros 3 registros):")
                for i, row in enumerate(rows[:3]):
                    self.stdout.write(f"    [{i+1}] {json.dumps(row, default=str, indent=8)[:200]}...")

                # Mostrar columnas disponibles
                if rows[0]:
                    self.stdout.write(f"\n  Columnas disponibles: {list(rows[0].keys())}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Error en query: {e}"))

        # Resumen
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Test completado"))
        self.stdout.write("=" * 60)

        if options["json"]:
            result = {
                "success": True,
                "config": {
                    "name": config.name,
                    "dataset_id": config.dataset_id,
                    "group_id": config.group_id,
                },
                "dataset_info": dataset_info if "dataset_info" in dir() else None,
                "records_found": len(rows) if "rows" in dir() else 0,
            }
            self.stdout.write(json.dumps(result, default=str, indent=2))
