from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from .models import IMAPConfiguration, EmailProcessingRule, IMAPProcessingLog
from .services import IMAPService


@admin.register(IMAPConfiguration)
class IMAPConfigurationAdmin(admin.ModelAdmin):
    """
    Admin para configuraciones IMAP.
    """

    list_display = [
        "name",
        "company",
        "host",
        "username",
        "is_active_display",
        "last_check_display",
        "check_interval_display",
        "test_connection_button",
    ]
    list_filter = ["is_active", "company", "use_ssl", "created_at"]
    search_fields = ["name", "host", "username", "company__name"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "last_check",
        "test_connection_result",
    ]
    fieldsets = (
        ("Información General", {"fields": ("name", "company", "is_active")}),
        (
            "Configuración del Servidor",
            {"fields": ("host", "port", "username", "password", "use_ssl")},
        ),
        (
            "Configuración de Carpetas",
            {
                "fields": ("inbox_folder", "processed_folder"),
                "description": "Configuración de las carpetas de email",
            },
        ),
        (
            "Configuración de Procesamiento",
            {
                "fields": ("check_interval", "max_emails_per_check"),
                "description": "Configuración del procesamiento automático",
            },
        ),
        (
            "Información del Sistema",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "last_check",
                    "test_connection_result",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_urls(self):
        """Agregar URLs personalizadas"""
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/test-connection/",
                self.admin_site.admin_view(self.test_connection_view),
                name="imap_configuration_test_connection",
            ),
            path(
                "<int:object_id>/process-now/",
                self.admin_site.admin_view(self.process_now_view),
                name="imap_configuration_process_now",
            ),
        ]
        return custom_urls + urls

    def is_active_display(self, obj):
        """Muestra el estado activo con colores"""
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Activa</span>')
        return format_html('<span style="color: red;">✗ Inactiva</span>')

    is_active_display.short_description = "Estado"

    def last_check_display(self, obj):
        """Muestra la última verificación de forma amigable"""
        if not obj.last_check:
            return format_html('<span style="color: orange;">Nunca</span>')

        time_diff = timezone.now() - obj.last_check

        if time_diff.total_seconds() < 3600:  # Menos de 1 hora
            minutes = int(time_diff.total_seconds() / 60)
            return format_html(
                '<span style="color: green;">Hace {} min</span>', minutes
            )
        elif time_diff.days == 0:  # Hoy
            hours = int(time_diff.total_seconds() / 3600)
            return format_html('<span style="color: blue;">Hace {} h</span>', hours)
        else:  # Más de un día
            return format_html(
                '<span style="color: red;">Hace {} días</span>', time_diff.days
            )

    last_check_display.short_description = "Última Verificación"

    def check_interval_display(self, obj):
        """Muestra el intervalo de verificación de forma amigable"""
        minutes = obj.check_interval // 60
        if minutes < 60:
            return f"{minutes} min"
        else:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if remaining_minutes > 0:
                return f"{hours}h {remaining_minutes}min"
            else:
                return f"{hours}h"

    check_interval_display.short_description = "Intervalo"

    def test_connection_button(self, obj):
        """Botón para probar la conexión"""
        return format_html(
            '<a class="button" href="{}">🔍 Probar</a>',
            reverse("admin:imap_configuration_test_connection", args=[obj.pk]),
        )

    test_connection_button.short_description = "Probar Conexión"

    def test_connection_result(self, obj):
        """Campo para mostrar resultado de prueba de conexión"""
        return "Use el botón 'Probar Conexión' para verificar la configuración"

    test_connection_result.short_description = "Resultado de Prueba"

    def test_connection_view(self, request, object_id):
        """Vista para probar conexión IMAP"""
        try:
            config = IMAPConfiguration.objects.get(pk=object_id)
            result = IMAPService.test_configuration(config)

            if result["success"]:
                messages.success(
                    request,
                    f"✅ Conexión exitosa a {config.name}! "
                    f'Tiempo: {result["connection_time"]:.2f}s, '
                    f'Carpetas: {result["folder_count"]}',
                )
            else:
                messages.error(
                    request, f'❌ Error conectando a {config.name}: {result["message"]}'
                )

        except IMAPConfiguration.DoesNotExist:
            messages.error(request, "Configuración IMAP no encontrada")
        except Exception as e:
            messages.error(request, f"Error inesperado: {str(e)}")

        return redirect("admin:imap_handler_imapconfiguration_change", object_id)

    def process_now_view(self, request, object_id):
        """Vista para procesar emails inmediatamente"""
        try:
            config = IMAPConfiguration.objects.get(pk=object_id)

            from .services import IMAPEmailHandler

            with IMAPEmailHandler(config) as handler:
                success = handler.process_emails()

            if success:
                messages.success(
                    request, f"✅ Procesamiento completado para {config.name}!"
                )
            else:
                messages.warning(
                    request,
                    f"⚠️ Procesamiento completado con advertencias para {config.name}",
                )

        except Exception as e:
            messages.error(request, f"❌ Error procesando {config.name}: {str(e)}")

        return redirect("admin:imap_handler_imapconfiguration_change", object_id)

    # Acciones personalizadas
    actions = [
        "test_all_connections",
        "process_all_configs",
        "test_connections_async",
        "process_configs_async",
        "activate_selected",
        "deactivate_selected",
    ]

    def test_all_connections(self, request, queryset):
        """Prueba todas las configuraciones seleccionadas"""
        success_count = 0
        for config in queryset:
            result = IMAPService.test_configuration(config)
            if result["success"]:
                success_count += 1

        total = queryset.count()
        if success_count == total:
            messages.success(
                request, f"✅ Todas las {total} configuraciones funcionan correctamente"
            )
        else:
            messages.warning(
                request,
                f"⚠️ {success_count}/{total} configuraciones funcionan correctamente",
            )

    test_all_connections.short_description = "🔍 Probar conexiones seleccionadas"

    def process_all_configs(self, request, queryset):
        """Procesa todas las configuraciones seleccionadas"""
        from .services import IMAPEmailHandler

        success_count = 0

        for config in queryset.filter(is_active=True):
            try:
                with IMAPEmailHandler(config) as handler:
                    if handler.process_emails():
                        success_count += 1
            except Exception:
                pass

        total = queryset.filter(is_active=True).count()
        messages.success(
            request, f"📧 Procesadas {success_count}/{total} configuraciones"
        )

    process_all_configs.short_description = (
        "📧 Procesar emails de configuraciones seleccionadas"
    )

    def test_connections_async(self, request, queryset):
        """Probar conexiones de manera asíncrona usando Celery"""
        try:
            from .tasks import test_imap_connection_task

            task_ids = []

            for config in queryset:
                task = test_imap_connection_task.delay(config.id)
                task_ids.append(task.id)

            messages.success(
                request,
                f"🚀 Pruebas de conexión iniciadas para {queryset.count()} configuraciones "
                f'(Tasks: {", ".join(task_ids[:3])}{"..." if len(task_ids) > 3 else ""})',
            )
        except ImportError:
            messages.error(
                request, "❌ Celery no está disponible. Usar versión síncrona."
            )
        except Exception as e:
            messages.error(request, f"❌ Error iniciando tareas async: {str(e)}")

    test_connections_async.short_description = "🚀 Probar conexiones (Async/Celery)"

    def process_configs_async(self, request, queryset):
        """Procesar configuraciones de manera asíncrona usando Celery"""
        try:
            from .tasks import process_single_account_task

            task_ids = []
            active_configs = queryset.filter(is_active=True)

            for config in active_configs:
                task = process_single_account_task.delay(config.id)
                task_ids.append(task.id)

            messages.success(
                request,
                f"🚀 Procesamiento iniciado para {active_configs.count()} configuraciones activas "
                f'(Tasks: {", ".join(task_ids[:3])}{"..." if len(task_ids) > 3 else ""})',
            )
        except ImportError:
            messages.error(
                request, "❌ Celery no está disponible. Usar versión síncrona."
            )
        except Exception as e:
            messages.error(request, f"❌ Error iniciando tareas async: {str(e)}")

    process_configs_async.short_description = "🚀 Procesar emails (Async/Celery)"

    def activate_selected(self, request, queryset):
        """Activar configuraciones seleccionadas"""
        updated = queryset.update(is_active=True)
        messages.success(request, f"✅ {updated} configuraciones activadas")

    activate_selected.short_description = "✅ Activar configuraciones seleccionadas"

    def deactivate_selected(self, request, queryset):
        """Desactivar configuraciones seleccionadas"""
        updated = queryset.update(is_active=False)
        messages.success(request, f"⏸️ {updated} configuraciones desactivadas")

    deactivate_selected.short_description = "⏸️ Desactivar configuraciones seleccionadas"


@admin.register(EmailProcessingRule)
class EmailProcessingRuleAdmin(admin.ModelAdmin):
    """
    Admin para reglas de procesamiento de emails.
    """

    list_display = [
        "name",
        "imap_config",
        "criteria_type",
        "criteria_preview",
        "priority_display",
        "assign_to_role",
        "is_active_display",
        "order",
    ]
    list_filter = [
        "criteria_type",
        "priority",
        "assign_to_role",
        "is_active",
        "imap_config__company",
    ]
    search_fields = ["name", "criteria_value", "imap_config__name"]
    readonly_fields = ["created_at"]
    fieldsets = (
        (
            "Información General",
            {"fields": ("name", "imap_config", "is_active", "order")},
        ),
        (
            "Criterios de Evaluación",
            {
                "fields": ("criteria_type", "criteria_value"),
                "description": "Define cuándo aplicar esta regla",
            },
        ),
        (
            "Acciones a Aplicar",
            {
                "fields": ("priority", "assign_to_role"),
                "description": "Qué hacer cuando se cumple el criterio",
            },
        ),
        (
            "Información del Sistema",
            {"fields": ("created_at",), "classes": ("collapse",)},
        ),
    )

    def criteria_preview(self, obj):
        """Muestra una preview del criterio"""
        value = obj.criteria_value
        if len(value) > 30:
            return f"{value[:30]}..."
        return value

    criteria_preview.short_description = "Valor del Criterio"

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

    def is_active_display(self, obj):
        """Muestra el estado activo con colores"""
        if obj.is_active:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')

    is_active_display.short_description = "Activa"


@admin.register(IMAPProcessingLog)
class IMAPProcessingLogAdmin(admin.ModelAdmin):
    """
    Admin para logs de procesamiento IMAP.
    """

    list_display = [
        "created_at",
        "imap_config",
        "status_display",
        "emails_processed",
        "emails_failed",
        "processing_time_display",
        "message_preview",
    ]
    list_filter = ["status", "imap_config", "created_at"]
    search_fields = ["message", "imap_config__name"]
    readonly_fields = [
        "imap_config",
        "status",
        "message",
        "emails_processed",
        "emails_failed",
        "processing_time",
        "created_at",
    ]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        """No permitir agregar logs manualmente"""
        return False

    def has_change_permission(self, request, obj=None):
        """Solo permitir ver los logs"""
        return False

    def status_display(self, obj):
        """Muestra el estado con colores"""
        colors = {
            "success": "green",
            "warning": "orange",
            "error": "red",
            "info": "blue",
        }
        color = colors.get(obj.status, "black")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_display.short_description = "Estado"

    def processing_time_display(self, obj):
        """Muestra el tiempo de procesamiento de forma amigable"""
        if obj.processing_time is None:
            return "N/A"

        if obj.processing_time < 1:
            return f"{obj.processing_time*1000:.0f}ms"
        elif obj.processing_time < 60:
            return f"{obj.processing_time:.1f}s"
        else:
            minutes = int(obj.processing_time // 60)
            seconds = obj.processing_time % 60
            return f"{minutes}m {seconds:.1f}s"

    processing_time_display.short_description = "Tiempo"

    def message_preview(self, obj):
        """Muestra una preview del mensaje"""
        if len(obj.message) > 60:
            return f"{obj.message[:60]}..."
        return obj.message

    message_preview.short_description = "Mensaje"
