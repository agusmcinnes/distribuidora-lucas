"""
Admin para Power BI Handler
Soporta tanto SuperAdmin (público) como TenantAdmin
"""

from django import forms
from django.contrib import admin, messages
from django.db import connection
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import (
    PowerBIGlobalConfig,
    PowerBITenantConfig,
    PowerBIAlertDefinition,
    PowerBIAlertInstance,
    PowerBIProcessingLog,
    # Legacy models (hidden from admin)
    PowerBIConfig,
    PowerBIAlert,
)


# =============================================================================
# Custom Forms with Textarea Widgets
# =============================================================================


class PowerBIAlertDefinitionForm(forms.ModelForm):
    """Form personalizado con widgets textarea para DAX y templates"""

    class Meta:
        model = PowerBIAlertDefinition
        fields = "__all__"
        widgets = {
            "dax_query": forms.Textarea(
                attrs={
                    "rows": 8,
                    "cols": 80,
                    "style": "font-family: monospace; background: #f8f9fa; "
                    "border: 1px solid #ced4da; padding: 10px;",
                    "placeholder": "EVALUATE TOPN(100, 'MiTabla')",
                }
            ),
            "openai_template": forms.Textarea(
                attrs={
                    "rows": 6,
                    "cols": 80,
                    "style": "background: #fff8e1; border: 1px solid #ffca28; padding: 10px;",
                    "placeholder": "Instrucciones para OpenAI sobre cómo formatear los datos...",
                }
            ),
            "example_output": forms.Textarea(
                attrs={
                    "rows": 6,
                    "cols": 80,
                    "style": "background: #e8f5e9; border: 1px solid #66bb6a; padding: 10px;",
                    "placeholder": "Ejemplo del mensaje formateado esperado...",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "cols": 80,
                }
            ),
        }


class PowerBITenantConfigForm(forms.ModelForm):
    """Form personalizado para configuración de tenant"""

    class Meta:
        model = PowerBITenantConfig
        fields = "__all__"
        widgets = {
            "default_openai_template": forms.Textarea(
                attrs={
                    "rows": 8,
                    "cols": 80,
                    "style": "background: #fff8e1; border: 1px solid #ffca28; padding: 10px;",
                }
            ),
            "default_example_output": forms.Textarea(
                attrs={
                    "rows": 6,
                    "cols": 80,
                    "style": "background: #e8f5e9; border: 1px solid #66bb6a; padding: 10px;",
                }
            ),
        }


# =============================================================================
# SuperAdmin - Public Schema (All Companies)
# =============================================================================


@admin.register(PowerBIGlobalConfig)
class PowerBIGlobalConfigAdmin(admin.ModelAdmin):
    """Admin para configuración global de Azure AD - Solo SuperAdmin"""

    list_display = [
        "name",
        "is_active_badge",
        "tenant_id_short",
        "client_id_short",
        "updated_at",
    ]
    list_filter = ["is_active"]
    search_fields = ["name", "tenant_id"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "General",
            {
                "fields": ("name", "is_active"),
            },
        ),
        (
            "Credenciales Azure AD",
            {
                "fields": ("tenant_id", "client_id", "client_secret"),
                "description": "Credenciales de la aplicación registrada en Azure AD. "
                "Estas credenciales son compartidas por todos los tenants.",
                "classes": ("wide",),
            },
        ),
        (
            "Configuración Power BI por Defecto",
            {
                "fields": ("default_group_id", "default_dataset_id", "default_dax_query"),
                "description": "Valores por defecto para las alertas. "
                "Las alertas usarán estos valores si no especifican los suyos propios.",
            },
        ),
        (
            "Información",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["test_connection"]

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 10px; border-radius: 4px;">Activo</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; '
            'padding: 3px 10px; border-radius: 4px;">Inactivo</span>'
        )

    is_active_badge.short_description = "Estado"

    def tenant_id_short(self, obj):
        if obj.tenant_id:
            return f"{obj.tenant_id[:8]}..."
        return "-"

    tenant_id_short.short_description = "Tenant ID"

    def client_id_short(self, obj):
        if obj.client_id:
            return f"{obj.client_id[:8]}..."
        return "-"

    client_id_short.short_description = "Client ID"

    def test_connection(self, request, queryset):
        """Acción para probar la conexión a Azure AD"""
        from .services import PowerBIAuthService

        for config in queryset:
            try:
                auth_service = PowerBIAuthService(config)
                auth_service.get_access_token()
                self.message_user(
                    request,
                    f"✅ Conexión exitosa para '{config.name}'",
                    level=messages.SUCCESS,
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"❌ Error en '{config.name}': {str(e)}",
                    level=messages.ERROR,
                )

    test_connection.short_description = "🔌 Probar conexión Azure AD"

    def has_module_permission(self, request):
        """Solo visible en esquema público"""
        return connection.schema_name == "public"


@admin.register(PowerBITenantConfig)
class PowerBITenantConfigAdmin(admin.ModelAdmin):
    """Admin para configuración de tenant - SuperAdmin ve todos"""

    form = PowerBITenantConfigForm
    list_display = ["company", "is_active_badge", "has_template_badge", "updated_at"]
    list_filter = ["is_active", "company"]
    search_fields = ["company__name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Empresa",
            {
                "fields": ("company", "is_active"),
            },
        ),
        (
            "Template OpenAI por Defecto",
            {
                "fields": ("default_openai_template", "default_example_output"),
                "description": "Estos templates se usarán para las alertas que no tengan uno propio configurado.",
            },
        ),
        (
            "Información",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 2px 8px; border-radius: 4px; font-size: 11px;">Activo</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; '
            'padding: 2px 8px; border-radius: 4px; font-size: 11px;">Inactivo</span>'
        )

    is_active_badge.short_description = "Estado"

    def has_template_badge(self, obj):
        has_template = bool(obj.default_openai_template)
        if has_template:
            return format_html(
                '<span style="color: #28a745;">✓ Configurado</span>'
            )
        return format_html('<span style="color: #6c757d;">○ Sin template</span>')

    has_template_badge.short_description = "Template OpenAI"

    def has_module_permission(self, request):
        return connection.schema_name == "public"


@admin.register(PowerBIAlertDefinition)
class PowerBIAlertDefinitionAdmin(admin.ModelAdmin):
    """Admin para definiciones de alertas - SuperAdmin ve todas"""

    form = PowerBIAlertDefinitionForm
    list_display = [
        "name",
        "company",
        "is_active_badge",
        "interval_display",
        "priority_badge",
        "chats_count",
        "last_check_display",
    ]
    list_filter = ["is_active", "company", "default_priority"]
    search_fields = ["name", "company__name", "description"]
    readonly_fields = ["created_at", "updated_at", "last_check"]
    filter_horizontal = ["telegram_chats"]
    autocomplete_fields = []  # No usar autocomplete para company

    fieldsets = (
        (
            "Configuración Básica",
            {
                "fields": ("company", "name", "is_active", "check_interval_minutes", "telegram_chats"),
                "description": "Solo necesitas configurar estos campos. Los valores técnicos se toman de la configuración global.",
            },
        ),
        (
            "⚙️ Configuración Avanzada (opcional)",
            {
                "fields": ("description", "group_id", "dataset_id", "dax_query", "default_priority"),
                "description": "Deja estos campos vacíos para usar los valores de la configuración global.",
                "classes": ("collapse",),
            },
        ),
        (
            "🤖 Formateo con OpenAI (opcional)",
            {
                "fields": ("openai_template", "example_output"),
                "description": "Si se dejan vacíos, se usará el template por defecto del tenant.",
                "classes": ("collapse",),
            },
        ),
        (
            "Información",
            {
                "fields": ("last_check", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["activate_alerts", "deactivate_alerts", "process_now", "test_query"]

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 2px 8px; border-radius: 4px; font-size: 11px;">Activa</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; '
            'padding: 2px 8px; border-radius: 4px; font-size: 11px;">Inactiva</span>'
        )

    is_active_badge.short_description = "Estado"

    def interval_display(self, obj):
        return f"{obj.check_interval_minutes} min"

    interval_display.short_description = "Intervalo"

    def priority_badge(self, obj):
        colors = {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#ffc107",
            "low": "#28a745",
        }
        color = colors.get(obj.default_priority, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_default_priority_display(),
        )

    priority_badge.short_description = "Prioridad"

    def chats_count(self, obj):
        count = obj.telegram_chats.count()
        if count == 0:
            return format_html('<span style="color: #dc3545;">0 chats</span>')
        return format_html(
            '<span style="color: #28a745;">{} chat{}</span>',
            count,
            "s" if count != 1 else "",
        )

    chats_count.short_description = "Chats"

    def last_check_display(self, obj):
        if obj.last_check:
            return obj.last_check.strftime("%d/%m %H:%M")
        return format_html('<span style="color: #6c757d;">Nunca</span>')

    last_check_display.short_description = "Última ejecución"

    def activate_alerts(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"✅ {updated} alertas activadas")

    activate_alerts.short_description = "✓ Activar alertas seleccionadas"

    def deactivate_alerts(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"⏸ {updated} alertas desactivadas")

    deactivate_alerts.short_description = "⏸ Desactivar alertas seleccionadas"

    def process_now(self, request, queryset):
        """Ejecuta las alertas seleccionadas inmediatamente"""
        from .tasks import process_single_alert

        for alert in queryset:
            process_single_alert.delay(alert.id)
            self.message_user(
                request,
                f"🚀 Alerta '{alert.name}' enviada a procesamiento",
                level=messages.SUCCESS,
            )

    process_now.short_description = "🚀 Ejecutar ahora"

    def test_query(self, request, queryset):
        """Prueba la query DAX de las alertas seleccionadas"""
        from .models import PowerBIGlobalConfig
        from .services import PowerBIQueryService

        global_config = PowerBIGlobalConfig.objects.filter(is_active=True).first()
        if not global_config:
            self.message_user(
                request,
                "❌ No hay configuración global de Power BI activa",
                level=messages.ERROR,
            )
            return

        for alert in queryset:
            try:
                # Usar métodos get_* para obtener valores con fallback
                group_id = alert.get_group_id()
                dataset_id = alert.get_dataset_id()
                dax_query = alert.get_dax_query()

                if not group_id or not dataset_id:
                    self.message_user(
                        request,
                        f"⚠️ '{alert.name}': Falta Group ID o Dataset ID (configura en la alerta o en configuración global)",
                        level=messages.WARNING,
                    )
                    continue

                query_service = PowerBIQueryService(
                    global_config=global_config,
                    group_id=group_id,
                    dataset_id=dataset_id,
                )
                rows = query_service.execute_query(dax_query)
                self.message_user(
                    request,
                    f"✅ '{alert.name}': Query exitosa - {len(rows)} registros encontrados",
                    level=messages.SUCCESS,
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"❌ '{alert.name}': Error - {str(e)[:100]}",
                    level=messages.ERROR,
                )

    test_query.short_description = "🔍 Probar Query DAX"

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Filtra los chats disponibles según la empresa seleccionada"""
        if db_field.name == "telegram_chats":
            # Si estamos editando un objeto existente, filtrar por su empresa
            if hasattr(self, "_obj") and self._obj:
                from telegram_bot.models import TelegramChat

                kwargs["queryset"] = TelegramChat.objects.filter(
                    company=self._obj.company
                )
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        self._obj = obj
        return super().get_form(request, obj, **kwargs)

    def has_module_permission(self, request):
        return connection.schema_name == "public"


@admin.register(PowerBIAlertInstance)
class PowerBIAlertInstanceAdmin(admin.ModelAdmin):
    """Admin para instancias de alertas - Solo lectura"""

    list_display = [
        "id",
        "alert_name",
        "company",
        "priority_badge",
        "status_badge",
        "created_at",
    ]
    list_filter = ["status", "priority", "company", "alert_definition", "created_at"]
    search_fields = ["powerbi_record_id", "formatted_message", "alert_definition__name"]
    readonly_fields = [
        "alert_definition",
        "company",
        "powerbi_record_id",
        "raw_data",
        "formatted_message",
        "priority",
        "status",
        "error_message",
        "powerbi_created_date",
        "processed_at",
        "sent_at",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Información",
            {
                "fields": (
                    "alert_definition",
                    "company",
                    "powerbi_record_id",
                    "priority",
                    "status",
                ),
            },
        ),
        (
            "Contenido",
            {
                "fields": ("formatted_message",),
            },
        ),
        (
            "Datos originales",
            {
                "fields": ("raw_data",),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "powerbi_created_date",
                    "processed_at",
                    "sent_at",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Errores",
            {
                "fields": ("error_message",),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["retry_send"]

    def alert_name(self, obj):
        return obj.alert_definition.name

    alert_name.short_description = "Alerta"

    def priority_badge(self, obj):
        colors = {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#ffc107",
            "low": "#28a745",
        }
        color = colors.get(obj.priority, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_priority_display(),
        )

    priority_badge.short_description = "Prioridad"

    def status_badge(self, obj):
        colors = {
            "pending": "#17a2b8",
            "processing": "#ffc107",
            "sent": "#28a745",
            "failed": "#dc3545",
            "ignored": "#6c757d",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Estado"

    def retry_send(self, request, queryset):
        """Reintenta enviar las instancias seleccionadas"""
        from .models import PowerBIGlobalConfig
        from .services import PowerBIAlertService

        global_config = PowerBIGlobalConfig.objects.filter(is_active=True).first()
        if not global_config:
            self.message_user(
                request,
                "❌ No hay configuración global de Power BI activa",
                level=messages.ERROR,
            )
            return

        service = PowerBIAlertService(global_config)
        success = 0
        failed = 0

        for instance in queryset.filter(status__in=["failed", "pending"]):
            try:
                if service._send_to_telegram(instance, instance.alert_definition):
                    success += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

        self.message_user(
            request,
            f"Reintento completado: {success} enviadas, {failed} fallidas",
            level=messages.SUCCESS if failed == 0 else messages.WARNING,
        )

    retry_send.short_description = "🔄 Reintentar envío"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return connection.schema_name == "public"


@admin.register(PowerBIProcessingLog)
class PowerBIProcessingLogAdmin(admin.ModelAdmin):
    """Admin para logs de procesamiento - Solo lectura"""

    list_display = [
        "id",
        "alert_definition_name",
        "status_badge",
        "records_fetched",
        "alerts_created",
        "alerts_sent",
        "alerts_failed",
        "processing_time_display",
        "created_at",
    ]
    list_filter = ["status", "alert_definition", "created_at"]
    search_fields = ["message", "alert_definition__name"]
    readonly_fields = [
        "alert_definition",
        "status",
        "message",
        "records_fetched",
        "records_new",
        "records_skipped",
        "alerts_created",
        "alerts_sent",
        "alerts_failed",
        "processing_time",
        "results_by_company",
        "created_at",
    ]
    date_hierarchy = "created_at"

    def alert_definition_name(self, obj):
        if obj.alert_definition:
            return obj.alert_definition.name
        return format_html('<span style="color: #6c757d;">(Global)</span>')

    alert_definition_name.short_description = "Alerta"

    def status_badge(self, obj):
        colors = {
            "success": "#28a745",
            "error": "#dc3545",
            "warning": "#ffc107",
            "info": "#17a2b8",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Estado"

    def processing_time_display(self, obj):
        if obj.processing_time:
            return f"{obj.processing_time:.2f}s"
        return "-"

    processing_time_display.short_description = "Tiempo"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return connection.schema_name == "public"


# =============================================================================
# TenantAdmin - Tenant Schema (Company-Specific)
# =============================================================================


class TenantPowerBIAlertDefinitionAdmin(admin.ModelAdmin):
    """
    Admin para definiciones de alertas en contexto de tenant.
    Solo muestra alertas de la empresa actual.
    """

    form = PowerBIAlertDefinitionForm
    list_display = [
        "name",
        "is_active_badge",
        "interval_display",
        "priority_badge",
        "chats_count",
        "last_check_display",
    ]
    list_filter = ["is_active", "default_priority"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at", "last_check"]
    filter_horizontal = ["telegram_chats"]

    # Ocultar company - se asigna automáticamente
    exclude = ["company"]

    fieldsets = (
        (
            "Configuración Básica",
            {
                "fields": ("name", "is_active", "check_interval_minutes", "telegram_chats"),
                "description": "Solo necesitas configurar estos campos. Los valores técnicos se toman de la configuración global.",
            },
        ),
        (
            "⚙️ Configuración Avanzada (opcional)",
            {
                "fields": ("description", "group_id", "dataset_id", "dax_query", "default_priority"),
                "description": "Deja estos campos vacíos para usar los valores de la configuración global.",
                "classes": ("collapse",),
            },
        ),
        (
            "🤖 Formateo con OpenAI (opcional)",
            {
                "fields": ("openai_template", "example_output"),
                "description": "Si se dejan vacíos, se usará el template por defecto del tenant.",
                "classes": ("collapse",),
            },
        ),
        (
            "Información",
            {
                "fields": ("last_check", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["activate_alerts", "deactivate_alerts", "process_now"]

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 2px 8px; border-radius: 4px; font-size: 11px;">Activa</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; '
            'padding: 2px 8px; border-radius: 4px; font-size: 11px;">Inactiva</span>'
        )

    is_active_badge.short_description = "Estado"

    def interval_display(self, obj):
        return f"{obj.check_interval_minutes} min"

    interval_display.short_description = "Intervalo"

    def priority_badge(self, obj):
        colors = {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#ffc107",
            "low": "#28a745",
        }
        color = colors.get(obj.default_priority, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_default_priority_display(),
        )

    priority_badge.short_description = "Prioridad"

    def chats_count(self, obj):
        count = obj.telegram_chats.count()
        if count == 0:
            return format_html('<span style="color: #dc3545;">0 chats</span>')
        return format_html(
            '<span style="color: #28a745;">{} chat{}</span>',
            count,
            "s" if count != 1 else "",
        )

    chats_count.short_description = "Chats"

    def last_check_display(self, obj):
        if obj.last_check:
            return obj.last_check.strftime("%d/%m %H:%M")
        return format_html('<span style="color: #6c757d;">Nunca</span>')

    last_check_display.short_description = "Última ejecución"

    def get_queryset(self, request):
        """Filtra por la empresa del schema actual"""
        qs = super().get_queryset(request)
        from company.models import Company

        try:
            company = Company.objects.get(schema_name=connection.schema_name)
            return qs.filter(company=company)
        except Company.DoesNotExist:
            return qs.none()

    def save_model(self, request, obj, form, change):
        """Asigna automáticamente la empresa del schema actual"""
        if not change:  # Nuevo objeto
            from company.models import Company

            obj.company = Company.objects.get(schema_name=connection.schema_name)
        super().save_model(request, obj, form, change)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Filtra los chats disponibles a los de la empresa actual"""
        if db_field.name == "telegram_chats":
            from company.models import Company
            from telegram_bot.models import TelegramChat

            try:
                company = Company.objects.get(schema_name=connection.schema_name)
                kwargs["queryset"] = TelegramChat.objects.filter(company=company)
            except Company.DoesNotExist:
                kwargs["queryset"] = TelegramChat.objects.none()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def activate_alerts(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"✅ {updated} alertas activadas")

    activate_alerts.short_description = "✓ Activar alertas seleccionadas"

    def deactivate_alerts(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"⏸ {updated} alertas desactivadas")

    deactivate_alerts.short_description = "⏸ Desactivar alertas seleccionadas"

    def process_now(self, request, queryset):
        """Ejecuta las alertas seleccionadas inmediatamente"""
        from .tasks import process_single_alert

        for alert in queryset:
            process_single_alert.delay(alert.id)
            self.message_user(
                request,
                f"🚀 Alerta '{alert.name}' enviada a procesamiento",
                level=messages.SUCCESS,
            )

    process_now.short_description = "🚀 Ejecutar ahora"

    def has_module_permission(self, request):
        """Solo visible en esquemas de tenant (no público)"""
        return connection.schema_name != "public"


class TenantPowerBIAlertInstanceAdmin(admin.ModelAdmin):
    """Admin para instancias de alertas en contexto de tenant"""

    list_display = [
        "id",
        "alert_name",
        "priority_badge",
        "status_badge",
        "created_at",
    ]
    list_filter = ["status", "priority", "alert_definition", "created_at"]
    search_fields = ["powerbi_record_id", "formatted_message"]
    readonly_fields = [
        "alert_definition",
        "company",
        "powerbi_record_id",
        "raw_data",
        "formatted_message",
        "priority",
        "status",
        "error_message",
        "processed_at",
        "sent_at",
        "created_at",
    ]
    date_hierarchy = "created_at"

    def alert_name(self, obj):
        return obj.alert_definition.name

    alert_name.short_description = "Alerta"

    def priority_badge(self, obj):
        colors = {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#ffc107",
            "low": "#28a745",
        }
        color = colors.get(obj.priority, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_priority_display(),
        )

    priority_badge.short_description = "Prioridad"

    def status_badge(self, obj):
        colors = {
            "pending": "#17a2b8",
            "processing": "#ffc107",
            "sent": "#28a745",
            "failed": "#dc3545",
            "ignored": "#6c757d",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Estado"

    def get_queryset(self, request):
        """Filtra por la empresa del schema actual"""
        qs = super().get_queryset(request)
        from company.models import Company

        try:
            company = Company.objects.get(schema_name=connection.schema_name)
            return qs.filter(company=company)
        except Company.DoesNotExist:
            return qs.none()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return connection.schema_name != "public"


# Registrar admin de tenant solo si no es público
# Esto se maneja dinámicamente por has_module_permission
