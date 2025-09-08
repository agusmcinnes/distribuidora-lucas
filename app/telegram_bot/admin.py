"""
Configuración del admin para el bot de Telegram
"""

from django.contrib import admin
from .models import TelegramConfig, TelegramChat, TelegramMessage


@admin.register(TelegramConfig)
class TelegramConfigAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Información Básica", {"fields": ("name", "is_active")}),
        ("Configuración del Bot", {"fields": ("bot_token",)}),
        ("Fechas", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = ["activate_config", "deactivate_config"]

    def activate_config(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"Se activaron {queryset.count()} configuraciones.")

    activate_config.short_description = "Activar configuraciones seleccionadas"

    def deactivate_config(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(
            request, f"Se desactivaron {queryset.count()} configuraciones."
        )

    deactivate_config.short_description = "Desactivar configuraciones seleccionadas"


@admin.register(TelegramChat)
class TelegramChatAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "chat_id",
        "chat_type",
        "alert_level",
        "email_alerts",
        "system_alerts",
        "is_active",
    ]
    list_filter = [
        "chat_type",
        "alert_level",
        "email_alerts",
        "system_alerts",
        "is_active",
        "created_at",
    ]
    search_fields = ["name", "chat_id", "username", "title"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Información del Chat",
            {"fields": ("name", "chat_id", "chat_type", "username", "title")},
        ),
        (
            "Configuración de Alertas",
            {"fields": ("alert_level", "email_alerts", "system_alerts", "is_active")},
        ),
        ("Fechas", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = [
        "activate_chats",
        "deactivate_chats",
        "enable_email_alerts",
        "disable_email_alerts",
    ]

    def activate_chats(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"Se activaron {queryset.count()} chats.")

    activate_chats.short_description = "Activar chats seleccionados"

    def deactivate_chats(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"Se desactivaron {queryset.count()} chats.")

    deactivate_chats.short_description = "Desactivar chats seleccionados"

    def enable_email_alerts(self, request, queryset):
        queryset.update(email_alerts=True)
        self.message_user(
            request, f"Se habilitaron alertas de email para {queryset.count()} chats."
        )

    enable_email_alerts.short_description = "Habilitar alertas de email"

    def disable_email_alerts(self, request, queryset):
        queryset.update(email_alerts=False)
        self.message_user(
            request,
            f"Se deshabilitaron alertas de email para {queryset.count()} chats.",
        )

    disable_email_alerts.short_description = "Deshabilitar alertas de email"


@admin.register(TelegramMessage)
class TelegramMessageAdmin(admin.ModelAdmin):
    list_display = [
        "subject",
        "chat",
        "message_type",
        "status",
        "retry_count",
        "sent_at",
        "created_at",
    ]
    list_filter = ["message_type", "status", "email_priority", "created_at", "sent_at"]
    search_fields = ["subject", "message", "email_subject", "email_sender"]
    readonly_fields = ["created_at", "updated_at", "sent_at", "telegram_message_id"]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Información del Mensaje",
            {"fields": ("chat", "message_type", "subject", "message", "status")},
        ),
        (
            "Información del Email (si aplica)",
            {
                "fields": ("email_subject", "email_sender", "email_priority"),
                "classes": ("collapse",),
            },
        ),
        (
            "Detalles Técnicos",
            {
                "fields": ("telegram_message_id", "error_message", "retry_count"),
                "classes": ("collapse",),
            },
        ),
        (
            "Fechas",
            {
                "fields": ("created_at", "updated_at", "sent_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["retry_failed_messages"]

    def retry_failed_messages(self, request, queryset):
        failed_messages = queryset.filter(status="failed")
        count = 0

        for message in failed_messages:
            if message.retry_count < 3:  # Máximo 3 reintentos
                # Aquí podrías implementar lógica para reenviar
                message.status = "retry"
                message.retry_count += 1
                message.save()
                count += 1

        self.message_user(request, f"Se marcaron {count} mensajes para reintento.")

    retry_failed_messages.short_description = "Reintentar mensajes fallidos"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("chat")
