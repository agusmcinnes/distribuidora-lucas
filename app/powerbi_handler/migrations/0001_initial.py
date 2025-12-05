# Generated manually for Power BI Handler

from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("company", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PowerBIConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        default="Default Power BI",
                        max_length=100,
                        unique=True,
                        verbose_name="Nombre de configuración",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        help_text="ID del tenant de Azure AD",
                        max_length=100,
                        verbose_name="Azure Tenant ID",
                    ),
                ),
                (
                    "client_id",
                    models.CharField(
                        help_text="ID de la aplicación registrada en Azure AD",
                        max_length=100,
                        verbose_name="Client ID",
                    ),
                ),
                (
                    "client_secret",
                    models.CharField(
                        help_text="Secreto de la aplicación (manejar con cuidado)",
                        max_length=255,
                        verbose_name="Client Secret",
                    ),
                ),
                (
                    "group_id",
                    models.CharField(
                        help_text="ID del workspace de Power BI",
                        max_length=100,
                        verbose_name="Workspace/Group ID",
                    ),
                ),
                (
                    "dataset_id",
                    models.CharField(
                        help_text="ID del dataset a consultar",
                        max_length=100,
                        verbose_name="Dataset ID",
                    ),
                ),
                (
                    "dax_query",
                    models.TextField(
                        default="EVALUATE TOPN(100, 'Alertas')",
                        help_text="Query DAX a ejecutar para obtener alertas",
                        verbose_name="Query DAX",
                    ),
                ),
                (
                    "field_mapping",
                    models.JSONField(
                        default=dict,
                        help_text='JSON con mapeo de campos del dataset. Ejemplo:\n        {\n            "record_id": "ID",\n            "company_identifier": "Empresa",\n            "subject": "Descripcion",\n            "body": "Detalle",\n            "priority": "Prioridad",\n            "date": "FechaCreacion"\n        }',
                        verbose_name="Mapeo de campos",
                    ),
                ),
                (
                    "check_interval",
                    models.IntegerField(
                        default=300,
                        help_text="Cada cuántos segundos se consulta Power BI",
                        validators=[django.core.validators.MinValueValidator(60)],
                        verbose_name="Intervalo de verificación (segundos)",
                    ),
                ),
                (
                    "max_records_per_check",
                    models.IntegerField(
                        default=100,
                        verbose_name="Máximo de registros por verificación",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Activo"),
                ),
                (
                    "last_check",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Última verificación"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Configuración de Power BI",
                "verbose_name_plural": "Configuraciones de Power BI",
            },
        ),
        migrations.CreateModel(
            name="PowerBIProcessingLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("success", "Éxito"),
                            ("error", "Error"),
                            ("warning", "Advertencia"),
                            ("info", "Información"),
                        ],
                        max_length=20,
                        verbose_name="Estado",
                    ),
                ),
                ("message", models.TextField(verbose_name="Mensaje")),
                (
                    "records_fetched",
                    models.IntegerField(default=0, verbose_name="Registros obtenidos"),
                ),
                (
                    "records_new",
                    models.IntegerField(default=0, verbose_name="Registros nuevos"),
                ),
                (
                    "records_skipped",
                    models.IntegerField(default=0, verbose_name="Registros omitidos"),
                ),
                (
                    "alerts_created",
                    models.IntegerField(default=0, verbose_name="Alertas creadas"),
                ),
                (
                    "alerts_failed",
                    models.IntegerField(default=0, verbose_name="Alertas fallidas"),
                ),
                (
                    "processing_time",
                    models.FloatField(
                        blank=True,
                        null=True,
                        verbose_name="Tiempo de procesamiento (segundos)",
                    ),
                ),
                (
                    "results_by_company",
                    models.JSONField(
                        default=dict, verbose_name="Resultados por empresa"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "config",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="processing_logs",
                        to="powerbi_handler.powerbiconfig",
                        verbose_name="Configuración",
                    ),
                ),
            ],
            options={
                "verbose_name": "Log de procesamiento Power BI",
                "verbose_name_plural": "Logs de procesamiento Power BI",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="PowerBIAlert",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "powerbi_record_id",
                    models.CharField(
                        help_text="Identificador único del registro en Power BI",
                        max_length=255,
                        verbose_name="ID de registro Power BI",
                    ),
                ),
                ("subject", models.CharField(max_length=500, verbose_name="Asunto")),
                (
                    "body",
                    models.TextField(blank=True, verbose_name="Contenido"),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("low", "Baja"),
                            ("medium", "Media"),
                            ("high", "Alta"),
                            ("critical", "Crítica"),
                        ],
                        default="medium",
                        max_length=20,
                        verbose_name="Prioridad",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pendiente"),
                            ("processing", "Procesando"),
                            ("sent", "Enviado"),
                            ("failed", "Fallido"),
                            ("ignored", "Ignorado"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="Estado",
                    ),
                ),
                (
                    "raw_data",
                    models.JSONField(
                        default=dict,
                        help_text="Datos crudos del registro de Power BI",
                        verbose_name="Datos originales",
                    ),
                ),
                (
                    "powerbi_created_date",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Fecha en Power BI"
                    ),
                ),
                (
                    "processed_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Procesado en"
                    ),
                ),
                (
                    "sent_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Enviado en"
                    ),
                ),
                (
                    "error_message",
                    models.TextField(blank=True, verbose_name="Mensaje de error"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="powerbi_alerts",
                        to="company.company",
                        verbose_name="Empresa",
                    ),
                ),
                (
                    "config",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="alerts",
                        to="powerbi_handler.powerbiconfig",
                        verbose_name="Configuración",
                    ),
                ),
            ],
            options={
                "verbose_name": "Alerta Power BI",
                "verbose_name_plural": "Alertas Power BI",
                "ordering": ["-created_at"],
                "unique_together": {("config", "powerbi_record_id")},
            },
        ),
        migrations.AddIndex(
            model_name="powerbialert",
            index=models.Index(
                fields=["powerbi_record_id"], name="powerbi_han_powerbi_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="powerbialert",
            index=models.Index(
                fields=["company", "status"], name="powerbi_han_company_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="powerbialert",
            index=models.Index(
                fields=["created_at"], name="powerbi_han_created_idx"
            ),
        ),
    ]
