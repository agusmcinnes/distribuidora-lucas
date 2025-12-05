"""
Modelos para la integración con Power BI
Sistema multi-tenant con alertas configurables por empresa
"""

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator


class PowerBIGlobalConfig(models.Model):
    """
    Configuración global de Azure AD para Power BI (una por instalación).
    Credenciales compartidas para todos los tenants.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        default="Default Power BI Config",
        verbose_name="Nombre de configuración",
    )

    # Azure AD / MSAL credentials
    tenant_id = models.CharField(
        max_length=100,
        verbose_name="Azure Tenant ID",
        help_text="ID del tenant de Azure AD",
    )
    client_id = models.CharField(
        max_length=100,
        verbose_name="Client ID",
        help_text="ID de la aplicación registrada en Azure AD",
    )
    client_secret = models.CharField(
        max_length=255,
        verbose_name="Client Secret",
        help_text="Secreto de la aplicación (manejar con cuidado)",
    )

    # Default Power BI settings (para alertas que no especifiquen los suyos)
    default_group_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Group/Workspace ID por defecto",
        help_text="ID del workspace de Power BI. Las alertas usarán este valor si no especifican uno propio.",
    )
    default_dataset_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Dataset ID por defecto",
        help_text="ID del dataset. Las alertas usarán este valor si no especifican uno propio.",
    )
    default_dax_query = models.TextField(
        blank=True,
        default="EVALUATE TOPN(100, 'VENTAS')",
        verbose_name="Query DAX por defecto",
        help_text="Query DAX por defecto. Las alertas usarán este valor si no especifican uno propio.",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración Global Power BI"
        verbose_name_plural = "Configuraciones Globales Power BI"

    def __str__(self):
        status = "Activo" if self.is_active else "Inactivo"
        return f"Power BI Global: {self.name} ({status})"


class PowerBITenantConfig(models.Model):
    """
    Configuración por tenant para Power BI.
    Almacena template OpenAI por defecto que las alertas pueden heredar.
    """

    company = models.OneToOneField(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="powerbi_tenant_config",
        verbose_name="Empresa",
    )

    # Default OpenAI template for this tenant
    default_openai_template = models.TextField(
        blank=True,
        verbose_name="Template OpenAI por defecto",
        help_text="""Template para formatear mensajes con OpenAI.
Este template se usará para todas las alertas que no tengan uno propio.
Ejemplo: "Eres un asistente que formatea alertas de ventas para Telegram.
Genera mensajes claros y concisos con los datos proporcionados."
        """,
    )

    default_example_output = models.TextField(
        blank=True,
        verbose_name="Ejemplo de salida por defecto",
        help_text="""Ejemplo del formato de mensaje esperado.
OpenAI usará este ejemplo como referencia para formatear los datos.
        """,
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración de Tenant Power BI"
        verbose_name_plural = "Configuraciones de Tenant Power BI"

    def __str__(self):
        return f"Config Power BI: {self.company.name}"


class PowerBIAlertDefinition(models.Model):
    """
    Definición individual de alerta - cada tenant puede tener N alertas.
    Cada alerta tiene su propio DAX query, dataset, schedule y destinatarios.
    """

    PRIORITY_CHOICES = [
        ("low", "Baja"),
        ("medium", "Media"),
        ("high", "Alta"),
        ("critical", "Crítica"),
    ]

    # Tenant relationship
    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="powerbi_alert_definitions",
        verbose_name="Empresa",
    )

    # Alert identification
    name = models.CharField(
        max_length=200,
        verbose_name="Nombre de la alerta",
        help_text="Nombre descriptivo para identificar esta alerta",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descripción",
        help_text="Descripción detallada del propósito de esta alerta",
    )

    # Power BI dataset configuration (per-alert, optional - uses global defaults if empty)
    group_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Workspace/Group ID",
        help_text="Deja vacío para usar el valor de la configuración global",
    )
    dataset_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Dataset ID",
        help_text="Deja vacío para usar el valor de la configuración global",
    )

    # DAX Query (optional - uses global default if empty)
    dax_query = models.TextField(
        blank=True,
        verbose_name="Query DAX",
        help_text="Deja vacío para usar el query por defecto de la configuración global",
    )


    # OpenAI Template (optional - inherits from tenant if empty)
    openai_template = models.TextField(
        blank=True,
        verbose_name="Template OpenAI",
        help_text="""Template específico para esta alerta.
Deja vacío para usar el template por defecto del tenant.
Describe cómo quieres que OpenAI formatee los datos para Telegram.
        """,
    )
    example_output = models.TextField(
        blank=True,
        verbose_name="Ejemplo de salida esperada",
        help_text="""Ejemplo de cómo debe verse el mensaje formateado.
OpenAI usará este ejemplo como guía para generar mensajes similares.
        """,
    )

    # Scheduling
    check_interval_minutes = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        verbose_name="Intervalo de verificación (minutos)",
        help_text="Cada cuántos minutos se ejecuta esta alerta",
    )
    last_check = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última verificación",
    )

    # Default priority for alerts from this definition
    default_priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="medium",
        verbose_name="Prioridad por defecto",
    )

    # Recipients (M2M to TelegramChat)
    telegram_chats = models.ManyToManyField(
        "telegram_bot.TelegramChat",
        related_name="powerbi_alert_definitions",
        blank=True,
        verbose_name="Chats destinatarios",
        help_text="Chats de Telegram que recibirán esta alerta",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Definición de Alerta"
        verbose_name_plural = "Definiciones de Alertas"
        unique_together = [["company", "name"]]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["last_check"]),
        ]

    def __str__(self):
        status = "Activa" if self.is_active else "Inactiva"
        return f"{self.company.name} - {self.name} ({status})"

    def is_due_for_check(self):
        """Verifica si es momento de ejecutar esta alerta según su intervalo"""
        if not self.last_check:
            return True
        elapsed_minutes = (timezone.now() - self.last_check).total_seconds() / 60
        return elapsed_minutes >= self.check_interval_minutes

    def get_group_id(self):
        """Obtiene el Group ID (propio o de la configuración global)"""
        if self.group_id:
            return self.group_id
        global_config = PowerBIGlobalConfig.objects.filter(is_active=True).first()
        return global_config.default_group_id if global_config else ""

    def get_dataset_id(self):
        """Obtiene el Dataset ID (propio o de la configuración global)"""
        if self.dataset_id:
            return self.dataset_id
        global_config = PowerBIGlobalConfig.objects.filter(is_active=True).first()
        return global_config.default_dataset_id if global_config else ""

    def get_dax_query(self):
        """Obtiene el Query DAX (propio o de la configuración global)"""
        if self.dax_query:
            return self.dax_query
        global_config = PowerBIGlobalConfig.objects.filter(is_active=True).first()
        return global_config.default_dax_query if global_config else "EVALUATE TOPN(100, 'VENTAS')"

    def get_openai_template(self):
        """Obtiene el template OpenAI (propio o heredado del tenant)"""
        if self.openai_template:
            return self.openai_template
        try:
            tenant_config = self.company.powerbi_tenant_config
            return tenant_config.default_openai_template
        except PowerBITenantConfig.DoesNotExist:
            return ""

    def get_example_output(self):
        """Obtiene el ejemplo de salida (propio o heredado del tenant)"""
        if self.example_output:
            return self.example_output
        try:
            tenant_config = self.company.powerbi_tenant_config
            return tenant_config.default_example_output
        except PowerBITenantConfig.DoesNotExist:
            return ""

    def mark_as_checked(self):
        """Marca el timestamp de última verificación"""
        self.last_check = timezone.now()
        self.save(update_fields=["last_check", "updated_at"])


class PowerBIAlertInstance(models.Model):
    """
    Instancia individual de alerta - un registro procesado de Power BI.
    Almacena tanto los datos crudos como el mensaje formateado.
    """

    STATUS_CHOICES = [
        ("pending", "Pendiente"),
        ("processing", "Procesando"),
        ("sent", "Enviado"),
        ("failed", "Fallido"),
        ("ignored", "Ignorado"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Baja"),
        ("medium", "Media"),
        ("high", "Alta"),
        ("critical", "Crítica"),
    ]

    # Relationships
    alert_definition = models.ForeignKey(
        PowerBIAlertDefinition,
        on_delete=models.CASCADE,
        related_name="instances",
        verbose_name="Definición de alerta",
    )
    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="powerbi_alert_instances",
        verbose_name="Empresa",
    )

    # Deduplication
    powerbi_record_id = models.CharField(
        max_length=255,
        verbose_name="ID de registro Power BI",
        help_text="Identificador único del registro en Power BI",
    )

    # Content (raw and formatted)
    raw_data = models.JSONField(
        default=dict,
        verbose_name="Datos originales",
        help_text="Datos crudos del registro de Power BI",
    )
    formatted_message = models.TextField(
        blank=True,
        verbose_name="Mensaje formateado",
        help_text="Mensaje formateado por OpenAI para enviar a Telegram",
    )

    # Status and priority
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="medium",
        verbose_name="Prioridad",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="Estado",
    )
    error_message = models.TextField(
        blank=True,
        verbose_name="Mensaje de error",
    )

    # Timestamps from Power BI
    powerbi_created_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha en Power BI",
    )

    # Processing timestamps
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Procesado en",
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Enviado en",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Instancia de Alerta"
        verbose_name_plural = "Instancias de Alertas"
        ordering = ["-created_at"]
        unique_together = [["alert_definition", "powerbi_record_id"]]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["powerbi_record_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.alert_definition.name}: {self.powerbi_record_id} ({self.status})"

    def mark_as_sent(self):
        """Marca la alerta como enviada"""
        self.status = "sent"
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "sent_at", "updated_at"])

    def mark_as_failed(self, error_message=""):
        """Marca la alerta como fallida"""
        self.status = "failed"
        self.error_message = error_message
        self.save(update_fields=["status", "error_message", "updated_at"])


class PowerBIProcessingLog(models.Model):
    """
    Log de ejecuciones de procesamiento de Power BI.
    Para monitoreo y debugging.
    """

    STATUS_CHOICES = [
        ("success", "Éxito"),
        ("error", "Error"),
        ("warning", "Advertencia"),
        ("info", "Información"),
    ]

    # Can be linked to a specific alert definition or be global
    alert_definition = models.ForeignKey(
        PowerBIAlertDefinition,
        on_delete=models.CASCADE,
        related_name="processing_logs",
        verbose_name="Definición de alerta",
        null=True,
        blank=True,
        help_text="Definición de alerta procesada (vacío para logs globales)",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name="Estado",
    )
    message = models.TextField(
        verbose_name="Mensaje",
    )

    # Metrics
    records_fetched = models.IntegerField(
        default=0,
        verbose_name="Registros obtenidos",
    )
    records_new = models.IntegerField(
        default=0,
        verbose_name="Registros nuevos",
    )
    records_skipped = models.IntegerField(
        default=0,
        verbose_name="Registros omitidos",
    )
    alerts_created = models.IntegerField(
        default=0,
        verbose_name="Alertas creadas",
    )
    alerts_sent = models.IntegerField(
        default=0,
        verbose_name="Alertas enviadas",
    )
    alerts_failed = models.IntegerField(
        default=0,
        verbose_name="Alertas fallidas",
    )
    processing_time = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Tiempo de procesamiento (segundos)",
    )

    # Breakdown by company (for global logs)
    results_by_company = models.JSONField(
        default=dict,
        verbose_name="Resultados por empresa",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log de procesamiento Power BI"
        verbose_name_plural = "Logs de procesamiento Power BI"
        ordering = ["-created_at"]

    def __str__(self):
        if self.alert_definition:
            return f"{self.alert_definition.name}: {self.status} - {self.created_at}"
        return f"Global: {self.status} - {self.created_at}"


# Keep old models temporarily for migration
# These will be removed after data migration

class PowerBIConfig(models.Model):
    """
    DEPRECATED: Configuración global de Power BI (legacy).
    Mantener temporalmente para migración de datos.
    Usar PowerBIGlobalConfig en su lugar.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        default="Default Power BI",
        verbose_name="Nombre de configuración",
    )

    tenant_id = models.CharField(
        max_length=100,
        verbose_name="Azure Tenant ID",
        help_text="ID del tenant de Azure AD",
    )
    client_id = models.CharField(
        max_length=100,
        verbose_name="Client ID",
        help_text="ID de la aplicación registrada en Azure AD",
    )
    client_secret = models.CharField(
        max_length=255,
        verbose_name="Client Secret",
        help_text="Secreto de la aplicación (manejar con cuidado)",
    )

    group_id = models.CharField(
        max_length=100,
        verbose_name="Workspace/Group ID",
        help_text="ID del workspace de Power BI",
    )
    dataset_id = models.CharField(
        max_length=100,
        verbose_name="Dataset ID",
        help_text="ID del dataset a consultar",
    )

    dax_query = models.TextField(
        verbose_name="Query DAX",
        help_text="Query DAX a ejecutar para obtener alertas",
        default="EVALUATE TOPN(100, 'Alertas')",
    )

    field_mapping = models.JSONField(
        default=dict,
        verbose_name="Mapeo de campos",
    )

    check_interval = models.IntegerField(
        default=300,
        validators=[MinValueValidator(60)],
        verbose_name="Intervalo de verificación (segundos)",
    )
    max_records_per_check = models.IntegerField(
        default=100,
        verbose_name="Máximo de registros por verificación",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    last_check = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última verificación",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "[LEGACY] Configuración de Power BI"
        verbose_name_plural = "[LEGACY] Configuraciones de Power BI"

    def __str__(self):
        return f"[LEGACY] Power BI: {self.name}"


class PowerBIAlert(models.Model):
    """
    DEPRECATED: Alertas generadas desde datos de Power BI (legacy).
    Mantener temporalmente para migración de datos.
    Usar PowerBIAlertInstance en su lugar.
    """

    PRIORITY_CHOICES = [
        ("low", "Baja"),
        ("medium", "Media"),
        ("high", "Alta"),
        ("critical", "Crítica"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pendiente"),
        ("processing", "Procesando"),
        ("sent", "Enviado"),
        ("failed", "Fallido"),
        ("ignored", "Ignorado"),
    ]

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="legacy_powerbi_alerts",
        verbose_name="Empresa",
        null=True,
        blank=True,
    )
    config = models.ForeignKey(
        PowerBIConfig,
        on_delete=models.CASCADE,
        related_name="legacy_alerts",
        verbose_name="Configuración",
    )

    powerbi_record_id = models.CharField(
        max_length=255,
        verbose_name="ID de registro Power BI",
    )

    subject = models.CharField(
        max_length=500,
        verbose_name="Asunto",
    )
    body = models.TextField(
        verbose_name="Contenido",
        blank=True,
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="medium",
        verbose_name="Prioridad",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="Estado",
    )

    raw_data = models.JSONField(
        default=dict,
        verbose_name="Datos originales",
    )

    powerbi_created_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha en Power BI",
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Procesado en",
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Enviado en",
    )
    error_message = models.TextField(
        blank=True,
        verbose_name="Mensaje de error",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "[LEGACY] Alerta Power BI"
        verbose_name_plural = "[LEGACY] Alertas Power BI"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[LEGACY] {self.subject[:50]}"
