from django.contrib import admin
from django.utils.html import format_html
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Company.
    """

    list_display = [
        "name",
        "get_active_users_count",
        "is_active_display",
        "created_at",
        "updated_at",
    ]
    list_filter = ["is_active", "created_at", "updated_at"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at", "get_active_users_count"]
    fieldsets = (
        ("Información Básica", {"fields": ("name", "is_active")}),
        (
            "Información del Sistema",
            {
                "fields": ("created_at", "updated_at", "get_active_users_count"),
                "classes": ("collapse",),
            },
        ),
    )

    def is_active_display(self, obj):
        """Muestra el estado activo con colores"""
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Activa</span>')
        return format_html('<span style="color: red;">✗ Inactiva</span>')

    is_active_display.short_description = "Estado"

    def get_queryset(self, request):
        """Optimiza las consultas incluyendo conteos"""
        return super().get_queryset(request).prefetch_related("users")

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
