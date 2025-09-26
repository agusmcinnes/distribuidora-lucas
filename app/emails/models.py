from django.db import models
from django.utils import timezone


class ReceivedEmail(models.Model):
    """
    Modelo que representa un email recibido del sistema IMAP.
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

    # Datos del email original
    sender = models.EmailField(
        verbose_name="Remitente", help_text="Dirección de email del remitente"
    )
    subject = models.CharField(
        max_length=500, verbose_name="Asunto", help_text="Asunto del email recibido"
    )
    body = models.TextField(
        verbose_name="Cuerpo del email", help_text="Contenido completo del email"
    )
    received_date = models.DateTimeField(
        verbose_name="Fecha de recepción",
        help_text="Fecha y hora en que se recibió el email",
    )

    # Datos de procesamiento
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="medium",
        verbose_name="Prioridad",
        help_text="Prioridad asignada al email para su procesamiento",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="Estado",
        help_text="Estado actual del procesamiento del email",
    )
    assigned_to = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_emails",
        verbose_name="Asignado a",
        help_text="Usuario al que se ha asignado esta alerta",
    )

    # Datos de seguimiento
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Procesado el",
        help_text="Fecha y hora en que se procesó el email",
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Enviado el",
        help_text="Fecha y hora en que se envió la alerta por Telegram",
    )
    error_message = models.TextField(
        blank=True,
        verbose_name="Mensaje de error",
        help_text="Mensaje de error en caso de fallo en el procesamiento",
    )

    # Metadatos
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Última actualización"
    )

    class Meta:
        verbose_name = "Email Recibido"
        verbose_name_plural = "Emails Recibidos"
        ordering = ["-received_date"]
        indexes = [
            models.Index(fields=["received_date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
        ]

    def __str__(self):
        return f"{self.subject[:50]}... ({self.sender}) - {self.get_status_display()}"

    def is_pending(self):
        """Verifica si el email está pendiente de procesamiento"""
        return self.status == "pending"

    is_pending.boolean = True
    is_pending.short_description = "Pendiente"

    def is_processed(self):
        """Verifica si el email ya fue procesado"""
        return self.status in ["sent", "failed", "ignored"]

    is_processed.boolean = True
    is_processed.short_description = "Procesado"

    def is_high_priority(self):
        """Verifica si el email tiene alta prioridad"""
        return self.priority in ["high", "critical"]

    is_high_priority.boolean = True
    is_high_priority.short_description = "Alta Prioridad"

    def time_since_received(self):
        """Calcula el tiempo transcurrido desde la recepción"""
        if self.received_date:
            delta = timezone.now() - self.received_date
            if delta.days > 0:
                return f"{delta.days} días"
            elif delta.seconds > 3600:
                hours = delta.seconds // 3600
                return f"{hours} horas"
            else:
                minutes = delta.seconds // 60
                return f"{minutes} minutos"
        return "N/A"

    time_since_received.short_description = "Tiempo desde recepción"

    def mark_as_sent(self):
        """Marca el email como enviado"""
        self.status = "sent"
        self.sent_at = timezone.now()
        self.save()

    def mark_as_failed(self, error_msg=""):
        """Marca el email como fallido"""
        self.status = "failed"
        self.error_message = error_msg
        self.save()

    def assign_to_user(self, user):
        """Asigna el email a un usuario específico"""
        self.assigned_to = user
        self.status = "processing"
        self.processed_at = timezone.now()
        self.save()
