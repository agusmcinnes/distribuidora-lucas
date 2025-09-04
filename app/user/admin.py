from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Role, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Role.
    """

    list_display = ["get_type_display", "type", "users_count", "created_at"]
    list_filter = ["type", "created_at"]
    search_fields = ["type", "description"]
    readonly_fields = ["created_at", "users_count"]
    fieldsets = (
        ("Información del Rol", {"fields": ("type", "description")}),
        (
            "Información del Sistema",
            {"fields": ("created_at", "users_count"), "classes": ("collapse",)},
        ),
    )

    def users_count(self, obj):
        """Cuenta los usuarios con este rol"""
        return obj.users.count()

    users_count.short_description = "Usuarios con este rol"

    def get_queryset(self, request):
        """Optimiza las consultas"""
        return (
            super()
            .get_queryset(request)
            .annotate(user_count=Count("users"))
            .prefetch_related("users")
        )


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo User.
    """

    list_display = [
        "name",
        "email",
        "role",
        "company",
        "is_active_display",
        "can_receive_alerts_display",
        "has_telegram",
        "created_at",
    ]
    list_filter = [
        "role__type",
        "company",
        "is_active",
        "can_receive_alerts",
        "created_at",
        "updated_at",
    ]
    search_fields = ["name", "email", "phone_number", "telegram_chat_id"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "is_manager",
        "is_supervisor",
        "has_telegram",
    ]
    fieldsets = (
        ("Información Personal", {"fields": ("name", "email", "phone_number")}),
        (
            "Configuración del Sistema",
            {"fields": ("role", "company", "is_active", "can_receive_alerts")},
        ),
        (
            "Telegram",
            {
                "fields": ("telegram_chat_id",),
                "description": "Configuración para el envío de alertas por Telegram",
            },
        ),
        (
            "Información del Sistema",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "is_manager",
                    "is_supervisor",
                    "has_telegram",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def is_active_display(self, obj):
        """Muestra el estado activo con colores"""
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Activo</span>')
        return format_html('<span style="color: red;">✗ Inactivo</span>')

    is_active_display.short_description = "Estado"

    def can_receive_alerts_display(self, obj):
        """Muestra si puede recibir alertas con colores"""
        if obj.can_receive_alerts:
            return format_html('<span style="color: green;">✓ Sí</span>')
        return format_html('<span style="color: orange;">✗ No</span>')

    can_receive_alerts_display.short_description = "Recibe Alertas"

    def get_queryset(self, request):
        """Optimiza las consultas"""
        return super().get_queryset(request).select_related("role", "company")

    # Acciones personalizadas
    actions = ["activate_users", "deactivate_users", "enable_alerts", "disable_alerts"]

    def activate_users(self, request, queryset):
        """Activa usuarios seleccionados"""
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} usuarios fueron activados exitosamente.")

    activate_users.short_description = "Activar usuarios seleccionados"

    def deactivate_users(self, request, queryset):
        """Desactiva usuarios seleccionados"""
        count = queryset.update(is_active=False)
        self.message_user(
            request, f"{count} usuarios fueron desactivados exitosamente."
        )

    deactivate_users.short_description = "Desactivar usuarios seleccionados"

    def enable_alerts(self, request, queryset):
        """Habilita alertas para usuarios seleccionados"""
        count = queryset.update(can_receive_alerts=True)
        self.message_user(request, f"Alertas habilitadas para {count} usuarios.")

    enable_alerts.short_description = "Habilitar alertas"

    def disable_alerts(self, request, queryset):
        """Deshabilita alertas para usuarios seleccionados"""
        count = queryset.update(can_receive_alerts=False)
        self.message_user(request, f"Alertas deshabilitadas para {count} usuarios.")

    disable_alerts.short_description = "Deshabilitar alertas"
