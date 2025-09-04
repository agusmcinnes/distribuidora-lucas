from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Q
from .models import ReceivedEmail


@admin.register(ReceivedEmail)
class ReceivedEmailAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo ReceivedEmail.
    """

    list_display = [
        "short_subject",
        "sender",
        "company",
        "priority_display",
        "status_display",
        "assigned_to",
        "time_since_received",
        "received_date",
    ]
    list_filter = [
        "status",
        "priority",
        "company",
        "assigned_to__role__type",
        "received_date",
        "created_at",
    ]
    search_fields = ["subject", "sender", "body", "assigned_to__name"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "time_since_received",
        "is_pending",
        "is_processed",
        "is_high_priority",
    ]
    date_hierarchy = "received_date"

    fieldsets = (
        (
            "Información del Email",
            {"fields": ("sender", "subject", "body", "received_date")},
        ),
        ("Procesamiento", {"fields": ("company", "priority", "status", "assigned_to")}),
        (
            "Seguimiento",
            {
                "fields": ("processed_at", "sent_at", "error_message"),
                "classes": ("collapse",),
            },
        ),
        (
            "Información del Sistema",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "time_since_received",
                    "is_pending",
                    "is_processed",
                    "is_high_priority",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def short_subject(self, obj):
        """Muestra el asunto truncado"""
        if len(obj.subject) > 50:
            return f"{obj.subject[:50]}..."
        return obj.subject

    short_subject.short_description = "Asunto"

    def priority_display(self, obj):
        """Muestra la prioridad con colores"""
        colors = {"low": "gray", "medium": "blue", "high": "orange", "critical": "red"}
        color = colors.get(obj.priority, "black")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_display(),
        )

    priority_display.short_description = "Prioridad"

    def status_display(self, obj):
        """Muestra el estado con colores"""
        colors = {
            "pending": "orange",
            "processing": "blue",
            "sent": "green",
            "failed": "red",
            "ignored": "gray",
        }
        color = colors.get(obj.status, "black")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_display.short_description = "Estado"

    def get_queryset(self, request):
        """Optimiza las consultas"""
        return (
            super()
            .get_queryset(request)
            .select_related("company", "assigned_to", "assigned_to__role")
        )

    # Acciones personalizadas
    actions = [
        "mark_as_high_priority",
        "mark_as_low_priority",
        "mark_as_processing",
        "mark_as_ignored",
        "assign_to_managers",
        "assign_to_supervisors",
    ]

    def mark_as_high_priority(self, request, queryset):
        """Marca emails como alta prioridad"""
        count = queryset.update(priority="high")
        self.message_user(request, f"{count} emails marcados como alta prioridad.")

    mark_as_high_priority.short_description = "Marcar como alta prioridad"

    def mark_as_low_priority(self, request, queryset):
        """Marca emails como baja prioridad"""
        count = queryset.update(priority="low")
        self.message_user(request, f"{count} emails marcados como baja prioridad.")

    mark_as_low_priority.short_description = "Marcar como baja prioridad"

    def mark_as_processing(self, request, queryset):
        """Marca emails como en procesamiento"""
        count = queryset.filter(status="pending").update(
            status="processing", processed_at=timezone.now()
        )
        self.message_user(request, f"{count} emails marcados como en procesamiento.")

    mark_as_processing.short_description = "Marcar como procesando"

    def mark_as_ignored(self, request, queryset):
        """Marca emails como ignorados"""
        count = queryset.update(status="ignored")
        self.message_user(request, f"{count} emails marcados como ignorados.")

    mark_as_ignored.short_description = "Marcar como ignorados"

    def assign_to_managers(self, request, queryset):
        """Asigna emails a managers de las respectivas empresas"""
        from user.models import User

        count = 0
        for email in queryset:
            managers = User.objects.filter(
                company=email.company,
                role__type="manager",
                is_active=True,
                can_receive_alerts=True,
            )
            if managers.exists():
                email.assign_to_user(managers.first())
                count += 1

        self.message_user(request, f"{count} emails asignados a managers.")

    assign_to_managers.short_description = "Asignar a managers"

    def assign_to_supervisors(self, request, queryset):
        """Asigna emails a supervisores de las respectivas empresas"""
        from user.models import User

        count = 0
        for email in queryset:
            supervisors = User.objects.filter(
                company=email.company,
                role__type="supervisor",
                is_active=True,
                can_receive_alerts=True,
            )
            if supervisors.exists():
                email.assign_to_user(supervisors.first())
                count += 1

        self.message_user(request, f"{count} emails asignados a supervisores.")

    assign_to_supervisors.short_description = "Asignar a supervisores"
