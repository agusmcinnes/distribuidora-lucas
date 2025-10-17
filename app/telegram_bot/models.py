"""
Modelos para la gestión del bot de Telegram
Estos modelos están en SHARED_APPS para permitir un bot centralizado
"""

from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator


class TelegramConfig(models.Model):
    """
    Configuración del bot de Telegram (simplificada)
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        default="Default Bot",
        verbose_name="Nombre de configuración",
    )
    bot_token = models.CharField(
        max_length=255,
        verbose_name="Token del Bot",
        help_text="Token proporcionado por BotFather",
    )
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración de Telegram"
        verbose_name_plural = "Configuraciones de Telegram"

    def __str__(self):
        return f"Bot: {self.name} {'(Activo)' if self.is_active else '(Inactivo)'}"


class TelegramChat(models.Model):
    """
    Chats de Telegram donde enviar alertas
    Cada chat está asociado a una empresa (tenant) específica y a un bot
    """

    CHAT_TYPE_CHOICES = [
        ("private", "Privado"),
        ("group", "Grupo"),
        ("supergroup", "Supergrupo"),
        ("channel", "Canal"),
    ]

    ALERT_LEVEL_CHOICES = [
        ("high", "Alta"),
        ("medium", "Media"),
        ("low", "Baja"),
        ("all", "Todas"),
    ]

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="telegram_chats",
        verbose_name="Empresa",
        help_text="Empresa a la que pertenece este chat",
        null=True,  # Temporal para migración inicial
        blank=True,
    )
    bot = models.ForeignKey(
        TelegramConfig,
        on_delete=models.CASCADE,
        related_name="chats",
        verbose_name="Bot de Telegram",
        help_text="Bot que enviará mensajes a este chat",
        null=True,  # Temporal para migración inicial
        blank=True,
    )
    name = models.CharField(max_length=100, verbose_name="Nombre del chat")
    chat_id = models.BigIntegerField(
        unique=True,
        verbose_name="ID del Chat",
        help_text="ID numérico del chat de Telegram",
    )
    chat_type = models.CharField(
        max_length=20,
        choices=CHAT_TYPE_CHOICES,
        default="private",
        verbose_name="Tipo de chat",
    )
    username = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Username",
        help_text="Username del chat (si aplica)",
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Título",
        help_text="Título del grupo/canal (si aplica)",
    )
    alert_level = models.CharField(
        max_length=10,
        choices=ALERT_LEVEL_CHOICES,
        default="all",
        verbose_name="Nivel de alertas",
        help_text="Qué nivel de alertas recibe este chat",
    )
    email_alerts = models.BooleanField(
        default=True,
        verbose_name="Alertas de email",
        help_text="Recibir alertas cuando lleguen nuevos emails",
    )
    system_alerts = models.BooleanField(
        default=False,
        verbose_name="Alertas del sistema",
        help_text="Recibir alertas de errores del sistema",
    )
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Chat de Telegram"
        verbose_name_plural = "Chats de Telegram"

    def __str__(self):
        return f"{self.name} - {self.company.name} ({self.chat_id})"


class TelegramMessage(models.Model):
    """
    Registro de mensajes enviados por Telegram
    Cada mensaje está asociado a una empresa para facilitar el tracking
    """

    STATUS_CHOICES = [
        ("pending", "Pendiente"),
        ("sent", "Enviado"),
        ("failed", "Fallido"),
        ("retry", "Reintentando"),
    ]

    MESSAGE_TYPE_CHOICES = [
        ("email_alert", "Alerta de Email"),
        ("system_alert", "Alerta del Sistema"),
        ("manual", "Manual"),
    ]

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="telegram_messages",
        verbose_name="Empresa",
        help_text="Empresa a la que pertenece este mensaje",
        null=True,  # Temporal para migración inicial
        blank=True,
    )
    chat = models.ForeignKey(
        TelegramChat, on_delete=models.CASCADE, verbose_name="Chat"
    )
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default="email_alert",
        verbose_name="Tipo de mensaje",
    )
    subject = models.CharField(max_length=255, verbose_name="Asunto")
    message = models.TextField(verbose_name="Mensaje")
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="pending", verbose_name="Estado"
    )
    telegram_message_id = models.BigIntegerField(
        blank=True, null=True, verbose_name="ID del mensaje en Telegram"
    )
    error_message = models.TextField(
        blank=True, null=True, verbose_name="Mensaje de error"
    )
    retry_count = models.IntegerField(default=0, verbose_name="Intentos de reenvío")
    sent_at = models.DateTimeField(blank=True, null=True, verbose_name="Enviado en")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Campos adicionales para alertas de email
    email_subject = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Asunto del email original"
    )
    email_sender = models.EmailField(
        blank=True, null=True, verbose_name="Remitente del email"
    )
    email_priority = models.CharField(
        max_length=10, blank=True, null=True, verbose_name="Prioridad del email"
    )

    class Meta:
        verbose_name = "Mensaje de Telegram"
        verbose_name_plural = "Mensajes de Telegram"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company.name}: {self.subject} -> {self.chat.name} ({self.status})"
