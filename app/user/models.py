from django.db import models
from django.core.validators import RegexValidator


class Role(models.Model):
    """
    Modelo que representa los roles de usuario en el sistema.
    """

    ROLE_CHOICES = [
        ("manager", "Manager"),
        ("supervisor", "Supervisor"),
        ("client", "Cliente"),
    ]

    type = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        unique=True,
        verbose_name="Tipo de rol",
        help_text="Define el tipo de rol en el sistema",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descripción",
        help_text="Descripción detallada del rol y sus responsabilidades",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de creación"
    )

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ["type"]

    def __str__(self):
        return self.get_type_display()


class User(models.Model):
    """
    Modelo que representa un usuario del sistema de alertas.
    """

    # Validador para número de teléfono
    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="El número de teléfono debe tener el formato: '+999999999'. Hasta 15 dígitos permitidos.",
    )

    name = models.CharField(
        max_length=150,
        verbose_name="Nombre completo",
        help_text="Nombre completo del usuario",
    )
    email = models.EmailField(
        unique=True, verbose_name="Email", help_text="Correo electrónico del usuario"
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        verbose_name="Número de teléfono",
        help_text="Número de teléfono con código de país",
    )
    telegram_chat_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Chat ID de Telegram",
        help_text="ID del chat de Telegram para envío de alertas",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="users",
        verbose_name="Rol",
        help_text="Rol del usuario en el sistema",
    )
    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="users",
        verbose_name="Empresa",
        help_text="Empresa a la que pertenece el usuario",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
        help_text="Indica si el usuario está activo en el sistema",
    )
    can_receive_alerts = models.BooleanField(
        default=True,
        verbose_name="Puede recibir alertas",
        help_text="Indica si el usuario puede recibir notificaciones de alertas",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Última actualización"
    )

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["name"]
        unique_together = ["email", "company"]

    def __str__(self):
        return f"{self.name} ({self.company.name}) - {self.role.get_type_display()}"

    def is_manager(self):
        """Verifica si el usuario es un manager"""
        return self.role.type == "manager"

    is_manager.boolean = True
    is_manager.short_description = "Es Manager"

    def is_supervisor(self):
        """Verifica si el usuario es un supervisor"""
        return self.role.type == "supervisor"

    is_supervisor.boolean = True
    is_supervisor.short_description = "Es Supervisor"

    def has_telegram(self):
        """Verifica si el usuario tiene configurado Telegram"""
        return bool(self.telegram_chat_id)

    has_telegram.boolean = True
    has_telegram.short_description = "Tiene Telegram"
