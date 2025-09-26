from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class IMAPConfiguration(models.Model):
    """
    Configuración para conexiones IMAP.
    Permite múltiples configuraciones para diferentes cuentas de email.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre de configuración",
        help_text="Nombre descriptivo para esta configuración IMAP",
    )
    host = models.CharField(
        max_length=255,
        verbose_name="Servidor IMAP",
        help_text="Dirección del servidor IMAP (ej: imap.gmail.com)",
    )
    port = models.IntegerField(
        default=993,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        verbose_name="Puerto",
        help_text="Puerto del servidor IMAP (993 para SSL, 143 para no SSL)",
    )
    username = models.CharField(
        max_length=255,
        verbose_name="Usuario/Email",
        help_text="Dirección de email o nombre de usuario",
    )
    password = models.CharField(
        max_length=255, verbose_name="Contraseña", help_text="Contraseña o app password"
    )
    use_ssl = models.BooleanField(
        default=True, verbose_name="Usar SSL", help_text="Usar conexión segura SSL/TLS"
    )
    inbox_folder = models.CharField(
        max_length=100,
        default="INBOX",
        verbose_name="Carpeta de entrada",
        help_text="Nombre de la carpeta de entrada",
    )
    processed_folder = models.CharField(
        max_length=100,
        default="Processed",
        blank=True,
        verbose_name="Carpeta procesados",
        help_text="Carpeta donde mover emails procesados (opcional)",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
        help_text="Indica si esta configuración está activa",
    )
    check_interval = models.IntegerField(
        default=300,
        validators=[MinValueValidator(60)],
        verbose_name="Intervalo de verificación (segundos)",
        help_text="Cada cuántos segundos verificar nuevos emails",
    )
    max_emails_per_check = models.IntegerField(
        default=50,
        validators=[MinValueValidator(1), MaxValueValidator(1000)],
        verbose_name="Máx. emails por verificación",
        help_text="Número máximo de emails a procesar por verificación",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Última actualización"
    )
    last_check = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última verificación",
        help_text="Última vez que se verificaron emails en esta cuenta",
    )

    class Meta:
        verbose_name = "Configuración IMAP"
        verbose_name_plural = "Configuraciones IMAP"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"

    def is_due_for_check(self):
        """Verifica si es hora de revisar emails"""
        if not self.last_check:
            return True

        time_since_check = timezone.now() - self.last_check
        return time_since_check.total_seconds() >= self.check_interval

    def mark_as_checked(self):
        """Marca la configuración como verificada ahora"""
        self.last_check = timezone.now()
        self.save(update_fields=["last_check"])


class EmailProcessingRule(models.Model):
    """
    Reglas para procesamiento automático de emails.
    Permite definir criterios para asignar prioridades y usuarios automáticamente.
    """

    PRIORITY_CHOICES = [
        ("low", "Baja"),
        ("medium", "Media"),
        ("high", "Alta"),
        ("critical", "Crítica"),
    ]

    CRITERIA_CHOICES = [
        ("subject_contains", "Asunto contiene"),
        ("sender_contains", "Remitente contiene"),
        ("body_contains", "Cuerpo contiene"),
        ("subject_regex", "Asunto coincide con regex"),
        ("sender_regex", "Remitente coincide con regex"),
    ]

    name = models.CharField(
        max_length=100,
        verbose_name="Nombre de la regla",
        help_text="Nombre descriptivo para esta regla",
    )
    imap_config = models.ForeignKey(
        IMAPConfiguration,
        on_delete=models.CASCADE,
        related_name="processing_rules",
        verbose_name="Configuración IMAP",
        help_text="Configuración IMAP a la que aplica esta regla",
    )
    criteria_type = models.CharField(
        max_length=20,
        choices=CRITERIA_CHOICES,
        verbose_name="Tipo de criterio",
        help_text="Tipo de criterio para evaluar el email",
    )
    criteria_value = models.CharField(
        max_length=500,
        verbose_name="Valor del criterio",
        help_text="Valor o patrón a buscar según el tipo de criterio",
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        verbose_name="Prioridad a asignar",
        help_text="Prioridad que se asignará si se cumple el criterio",
    )
    assign_to_role = models.CharField(
        max_length=20,
        choices=[("manager", "Manager"), ("supervisor", "Supervisor")],
        null=True,
        blank=True,
        verbose_name="Asignar a rol",
        help_text="Rol al que asignar automáticamente (opcional)",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
        help_text="Indica si esta regla está activa",
    )
    order = models.IntegerField(
        default=0,
        verbose_name="Orden",
        help_text="Orden de evaluación de las reglas (menor número = mayor prioridad)",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de creación"
    )

    class Meta:
        verbose_name = "Regla de procesamiento"
        verbose_name_plural = "Reglas de procesamiento"
        ordering = ["imap_config", "order", "name"]

    def __str__(self):
        return f"{self.name} ({self.imap_config.name})"

    def evaluate(self, email_data):
        """
        Evalúa si un email cumple con esta regla.

        Args:
            email_data (dict): Datos del email con keys: subject, sender, body

        Returns:
            bool: True si el email cumple con el criterio
        """
        import re

        criteria_map = {
            "subject_contains": lambda: self.criteria_value.lower()
            in email_data.get("subject", "").lower(),
            "sender_contains": lambda: self.criteria_value.lower()
            in email_data.get("sender", "").lower(),
            "body_contains": lambda: self.criteria_value.lower()
            in email_data.get("body", "").lower(),
            "subject_regex": lambda: bool(
                re.search(
                    self.criteria_value, email_data.get("subject", ""), re.IGNORECASE
                )
            ),
            "sender_regex": lambda: bool(
                re.search(
                    self.criteria_value, email_data.get("sender", ""), re.IGNORECASE
                )
            ),
        }

        try:
            return criteria_map.get(self.criteria_type, lambda: False)()
        except Exception:
            return False


class IMAPProcessingLog(models.Model):
    """
    Log de procesamiento IMAP para seguimiento y debugging.
    """

    STATUS_CHOICES = [
        ("success", "Éxito"),
        ("error", "Error"),
        ("warning", "Advertencia"),
        ("info", "Información"),
    ]

    imap_config = models.ForeignKey(
        IMAPConfiguration,
        on_delete=models.CASCADE,
        related_name="processing_logs",
        verbose_name="Configuración IMAP",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, verbose_name="Estado"
    )
    message = models.TextField(
        verbose_name="Mensaje", help_text="Mensaje de log detallado"
    )
    emails_processed = models.IntegerField(
        default=0,
        verbose_name="Emails procesados",
        help_text="Número de emails procesados en esta ejecución",
    )
    emails_failed = models.IntegerField(
        default=0,
        verbose_name="Emails fallidos",
        help_text="Número de emails que fallaron al procesar",
    )
    processing_time = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Tiempo de procesamiento (segundos)",
        help_text="Tiempo que tomó el procesamiento",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de creación"
    )

    class Meta:
        verbose_name = "Log de procesamiento IMAP"
        verbose_name_plural = "Logs de procesamiento IMAP"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.imap_config.name} - {self.get_status_display()} ({self.created_at})"
        )
