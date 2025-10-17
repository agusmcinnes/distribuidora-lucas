"""
Configuración del admin para el bot de Telegram
Adaptado para arquitectura multi-tenant con bot centralizado
"""

from django.contrib import admin
from django.db import connection
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import TelegramConfig, TelegramChat, TelegramMessage


# ==============================================================================
# ADMIN PARA ESQUEMA PÚBLICO (Superadmin)
# ==============================================================================


@admin.register(TelegramConfig)
class TelegramConfigAdmin(admin.ModelAdmin):
    """
    Admin para configuración del bot de Telegram
    Solo visible en el esquema público para el superadmin
    """

    list_display = ["name", "is_active", "bot_status_display", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at", "bot_info_display"]

    fieldsets = (
        ("Información Básica", {"fields": ("name", "is_active")}),
        (
            "Configuración del Bot",
            {
                "fields": ("bot_token",),
                "description": "Token proporcionado por BotFather en Telegram",
            },
        ),
        (
            "Información del Bot",
            {"fields": ("bot_info_display",), "classes": ("collapse",)},
        ),
        ("Fechas", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = ["activate_config", "deactivate_config", "test_bot_connection"]

    def get_queryset(self, request):
        """Solo mostrar en esquema público"""
        qs = super().get_queryset(request)
        # Solo mostrar en esquema público
        if connection.schema_name != "public":
            return qs.none()
        return qs

    def has_module_permission(self, request):
        """Solo mostrar el módulo en esquema público"""
        return connection.schema_name == "public"

    def bot_status_display(self, obj):
        """Muestra el estado del bot con colores"""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Activo</span>'
            )
        return format_html(
            '<span style="color: gray;">○ Inactivo</span>'
        )

    bot_status_display.short_description = "Estado del Bot"

    def bot_info_display(self, obj):
        """Muestra información del bot (si está disponible)"""
        try:
            import requests

            url = f"https://api.telegram.org/bot{obj.bot_token}/getMe"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    bot_info = data.get("result", {})
                    info_html = f"""
                    <div style="font-family: monospace; background: #f5f5f5; padding: 10px; border-radius: 5px;">
                        <p><strong>🤖 Bot Username:</strong> @{bot_info.get('username', 'N/A')}</p>
                        <p><strong>📝 Nombre:</strong> {bot_info.get('first_name', 'N/A')}</p>
                        <p><strong>🆔 ID:</strong> {bot_info.get('id', 'N/A')}</p>
                        <p><strong>✅ Estado:</strong> <span style="color: green;">Conectado</span></p>
                    </div>
                    """
                    return mark_safe(info_html)
                else:
                    return format_html(
                        '<span style="color: red;">❌ Error: {}</span>',
                        data.get("description", "Unknown error"),
                    )
            else:
                return format_html(
                    '<span style="color: red;">❌ Error HTTP: {}</span>',
                    response.status_code,
                )
        except Exception as e:
            return format_html(
                '<span style="color: orange;">⚠️ No se pudo verificar: {}</span>',
                str(e),
            )

    bot_info_display.short_description = "Información del Bot"

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

    def test_bot_connection(self, request, queryset):
        """Probar conexión del bot"""
        for config in queryset:
            try:
                import requests

                url = f"https://api.telegram.org/bot{config.bot_token}/getMe"
                response = requests.get(url, timeout=5)

                if response.status_code == 200 and response.json().get("ok"):
                    self.message_user(
                        request,
                        f"✅ Bot '{config.name}' está funcionando correctamente.",
                        level="success",
                    )
                else:
                    self.message_user(
                        request,
                        f"❌ Bot '{config.name}' no responde correctamente.",
                        level="error",
                    )
            except Exception as e:
                self.message_user(
                    request,
                    f"❌ Error probando bot '{config.name}': {str(e)}",
                    level="error",
                )

    test_bot_connection.short_description = "Probar conexión del bot"


class PublicTelegramChatAdmin(admin.ModelAdmin):
    """
    Admin para chats de Telegram en esquema público
    Permite al superadmin ver todos los chats de todas las empresas
    """

    list_display = [
        "name",
        "company",
        "bot",
        "chat_id",
        "chat_type",
        "alert_level",
        "email_alerts",
        "system_alerts",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "company",
        "bot",
        "chat_type",
        "alert_level",
        "email_alerts",
        "system_alerts",
        "is_active",
        "created_at",
    ]
    search_fields = ["name", "chat_id", "username", "title", "company__name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Configuración Básica",
            {"fields": ("company", "bot")},
        ),
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

    def get_queryset(self, request):
        """Solo mostrar en esquema público"""
        qs = super().get_queryset(request)
        if connection.schema_name != "public":
            return qs.none()
        return qs

    def has_module_permission(self, request):
        """Solo mostrar el módulo en esquema público"""
        return connection.schema_name == "public"

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


class PublicTelegramMessageAdmin(admin.ModelAdmin):
    """
    Admin para mensajes de Telegram en esquema público
    Permite al superadmin ver todos los mensajes de todas las empresas
    """

    list_display = [
        "company",
        "subject",
        "chat",
        "message_type",
        "status",
        "retry_count",
        "sent_at",
        "created_at",
    ]
    list_filter = [
        "company",
        "message_type",
        "status",
        "email_priority",
        "created_at",
        "sent_at",
    ]
    search_fields = [
        "subject",
        "message",
        "email_subject",
        "email_sender",
        "company__name",
    ]
    readonly_fields = ["created_at", "updated_at", "sent_at", "telegram_message_id"]
    date_hierarchy = "created_at"
    raw_id_fields = ["company", "chat"]

    fieldsets = (
        ("Empresa", {"fields": ("company",)}),
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

    def get_queryset(self, request):
        """Solo mostrar en esquema público"""
        qs = super().get_queryset(request)
        if connection.schema_name != "public":
            return qs.none()
        return qs.select_related("chat", "company")

    def has_module_permission(self, request):
        """Solo mostrar el módulo en esquema público"""
        return connection.schema_name == "public"

    def retry_failed_messages(self, request, queryset):
        failed_messages = queryset.filter(status="failed")
        count = 0

        for message in failed_messages:
            if message.retry_count < 3:  # Máximo 3 reintentos
                message.status = "retry"
                message.retry_count += 1
                message.save()
                count += 1

        self.message_user(request, f"Se marcaron {count} mensajes para reintento.")

    retry_failed_messages.short_description = "Reintentar mensajes fallidos"


# ==============================================================================
# ADMIN PARA ESQUEMA TENANT (Admin de empresa)
# ==============================================================================


class TenantTelegramChatAdmin(admin.ModelAdmin):
    """
    Admin para chats de Telegram en esquema tenant
    Solo muestra los chats de la empresa actual
    """

    list_display = [
        "name",
        "chat_id",
        "bot",
        "chat_type",
        "alert_level",
        "email_alerts",
        "system_alerts",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "bot",
        "chat_type",
        "alert_level",
        "email_alerts",
        "system_alerts",
        "is_active",
        "created_at",
    ]
    search_fields = ["name", "chat_id", "username", "title"]
    readonly_fields = ["created_at", "updated_at", "setup_instructions"]

    fieldsets = (
        (
            "📋 Instrucciones de Configuración",
            {
                "fields": ("setup_instructions",),
                "description": "Sigue estos pasos para configurar tu chat de Telegram",
            },
        ),
        (
            "Configuración Básica",
            {
                "fields": ("company", "bot"),
                "description": "Selecciona la empresa y el bot para este chat",
            },
        ),
        (
            "Información del Chat",
            {
                "fields": ("name", "chat_id", "chat_type", "username", "title"),
                "description": "Información básica del chat de Telegram",
            },
        ),
        (
            "Configuración de Alertas",
            {
                "fields": ("alert_level", "email_alerts", "system_alerts", "is_active"),
                "description": "Configura qué tipo de alertas recibir",
            },
        ),
        ("Fechas", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = [
        "activate_chats",
        "deactivate_chats",
        "enable_email_alerts",
        "test_send_message",
    ]

    def get_queryset(self, request):
        """Mostrar chats según el esquema"""
        qs = super().get_queryset(request)

        # Si estamos en público, mostrar todos (como superadmin)
        if connection.schema_name == "public":
            return qs.all()

        # Si estamos en tenant, filtrar por empresa actual
        from company.models import Company
        try:
            current_company = Company.objects.get(schema_name=connection.schema_name)
            return qs.filter(company=current_company)
        except Company.DoesNotExist:
            return qs.none()

    def has_module_permission(self, request):
        """Mostrar el módulo en todos los esquemas"""
        return True

    def setup_instructions(self, obj):
        """Muestra instrucciones para configurar Telegram"""
        instructions_html = """
        <div style="font-family: Arial; background: #e8f5e9; padding: 20px; border-radius: 8px; border: 2px solid #4caf50;">
            <h3 style="color: #2e7d32; margin-top: 0;">🚀 Cómo configurar tu chat de Telegram</h3>

            <div style="background: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h4 style="color: #1976d2; margin-top: 0;">📱 Paso 1: Busca el bot en Telegram</h4>
                <p>Abre Telegram y busca el bot de notificaciones de tu empresa.</p>
                <p><strong>Tip:</strong> Pregunta al administrador del sistema el nombre del bot.</p>
            </div>

            <div style="background: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h4 style="color: #1976d2; margin-top: 0;">👥 Paso 2: Crea un grupo o usa uno existente</h4>
                <ol>
                    <li>Crea un nuevo grupo en Telegram</li>
                    <li>Agregar el bot al grupo</li>
                    <li>Asegúrate de que el bot tenga permisos para enviar mensajes</li>
                </ol>
            </div>

            <div style="background: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h4 style="color: #1976d2; margin-top: 0;">🔢 Paso 3: Obtén el Chat ID</h4>
                <p>En el grupo, envía el comando:</p>
                <code style="background: #f5f5f5; padding: 5px 10px; border-radius: 3px; font-size: 14px;">/get_chat_id</code>
                <p style="margin-top: 10px;">El bot responderá con el ID del chat. <strong>Copia ese número.</strong></p>
            </div>

            <div style="background: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h4 style="color: #1976d2; margin-top: 0;">✅ Paso 4: Registra el chat aquí</h4>
                <ol>
                    <li>Haz clic en "Agregar Chat de Telegram"</li>
                    <li>Pega el Chat ID que obtuviste</li>
                    <li>Dale un nombre descriptivo</li>
                    <li>Configura las alertas que deseas recibir</li>
                    <li>Guarda los cambios</li>
                </ol>
            </div>

            <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; border: 1px solid #ffc107;">
                <p style="margin: 0;"><strong>⚠️ Importante:</strong> Una vez configurado, el bot enviará notificaciones automáticamente cuando lleguen nuevos emails a tu empresa.</p>
            </div>
        </div>
        """
        return mark_safe(instructions_html)

    setup_instructions.short_description = "Guía de Configuración"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customizar los selectores de ForeignKey"""
        if db_field.name == "company":
            # Obtener la empresa actual del tenant
            from company.models import Company

            try:
                current_company = Company.objects.get(schema_name=connection.schema_name)
                # Mostrar solo la empresa actual por defecto
                kwargs["queryset"] = Company.objects.filter(id=current_company.id)
                kwargs["initial"] = current_company.id
            except Company.DoesNotExist:
                kwargs["queryset"] = Company.objects.none()

        elif db_field.name == "bot":
            # Obtener bots del esquema público
            original_schema = connection.schema_name
            try:
                connection.set_schema("public")
                # Mostrar solo bots activos
                kwargs["queryset"] = TelegramConfig.objects.filter(is_active=True)
                # Establecer el primer bot activo como default
                active_bot = TelegramConfig.objects.filter(is_active=True).first()
                if active_bot:
                    kwargs["initial"] = active_bot.id
            finally:
                connection.set_schema(original_schema)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        """Auto-asignar la empresa actual y bot si no están establecidos"""
        if not change:  # Solo en creación
            from company.models import Company

            # Auto-asignar empresa si no está establecida
            if not obj.company:
                try:
                    obj.company = Company.objects.get(schema_name=connection.schema_name)
                except Company.DoesNotExist:
                    pass

            # Auto-asignar bot activo si no está establecido
            if not obj.bot:
                original_schema = connection.schema_name
                try:
                    connection.set_schema("public")
                    obj.bot = TelegramConfig.objects.filter(is_active=True).first()
                finally:
                    connection.set_schema(original_schema)

        super().save_model(request, obj, form, change)

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

    def test_send_message(self, request, queryset):
        """Enviar mensaje de prueba"""
        from .services import TelegramNotificationService

        for chat in queryset:
            try:
                # Obtener servicio
                service = TelegramNotificationService()

                # Mensaje de prueba
                test_message = f"""
🧪 <b>Mensaje de Prueba</b>

Este es un mensaje de prueba desde el panel de administración.

✅ Tu chat está correctamente configurado y recibiendo notificaciones.

<b>Chat:</b> {chat.name}
<b>ID:</b> {chat.chat_id}
<b>Empresa:</b> {chat.company.name}
                """

                # Enviar
                success = service._send_message(chat.chat_id, test_message)

                if success:
                    self.message_user(
                        request,
                        f"✅ Mensaje de prueba enviado a '{chat.name}'",
                        level="success",
                    )
                else:
                    self.message_user(
                        request,
                        f"❌ Error enviando mensaje a '{chat.name}'",
                        level="error",
                    )
            except Exception as e:
                self.message_user(
                    request,
                    f"❌ Error con chat '{chat.name}': {str(e)}",
                    level="error",
                )

    test_send_message.short_description = "Enviar mensaje de prueba"


class TenantTelegramMessageAdmin(admin.ModelAdmin):
    """
    Admin para mensajes de Telegram en esquema tenant
    Solo muestra los mensajes de la empresa actual
    """

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
    readonly_fields = [
        "created_at",
        "updated_at",
        "sent_at",
        "telegram_message_id",
        "company",
    ]
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
        ("Empresa", {"fields": ("company",), "classes": ("collapse",)}),
        (
            "Fechas",
            {
                "fields": ("created_at", "updated_at", "sent_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["retry_failed_messages"]

    def get_queryset(self, request):
        """Solo mostrar mensajes de la empresa actual en tenant"""
        qs = super().get_queryset(request)

        # Solo en esquemas tenant (no público)
        if connection.schema_name == "public":
            return qs.none()

        # Obtener la empresa actual del tenant
        from company.models import Company
        try:
            current_company = Company.objects.get(schema_name=connection.schema_name)
            return qs.filter(company=current_company).select_related("chat")
        except Company.DoesNotExist:
            return qs.none()

    def has_module_permission(self, request):
        """Solo mostrar el módulo en esquemas tenant"""
        return connection.schema_name != "public"

    def has_add_permission(self, request):
        """No permitir agregar mensajes manualmente desde el admin"""
        return False

    def retry_failed_messages(self, request, queryset):
        failed_messages = queryset.filter(status="failed")
        count = 0

        for message in failed_messages:
            if message.retry_count < 3:  # Máximo 3 reintentos
                message.status = "retry"
                message.retry_count += 1
                message.save()
                count += 1

        self.message_user(request, f"Se marcaron {count} mensajes para reintento.")

    retry_failed_messages.short_description = "Reintentar mensajes fallidos"


# ==============================================================================
# REGISTRAR ADMINS
# ==============================================================================

# TelegramConfig ya está registrado con @admin.register arriba

# Registrar TelegramChat y TelegramMessage con admin dinámico
# El admin correcto se seleccionará según el esquema en runtime

class DynamicTelegramChatAdmin(admin.ModelAdmin):
    """Admin dinámico que delega al admin correcto según el esquema"""

    def __new__(cls, model, admin_site):
        # Seleccionar el admin correcto según el esquema actual
        if connection.schema_name == "public":
            return PublicTelegramChatAdmin(model, admin_site)
        else:
            return TenantTelegramChatAdmin(model, admin_site)


class DynamicTelegramMessageAdmin(admin.ModelAdmin):
    """Admin dinámico que delega al admin correcto según el esquema"""

    def __new__(cls, model, admin_site):
        # Seleccionar el admin correcto según el esquema actual
        if connection.schema_name == "public":
            return PublicTelegramMessageAdmin(model, admin_site)
        else:
            return TenantTelegramMessageAdmin(model, admin_site)


# Registrar con los admins estándar por defecto (tenant)
# Los métodos sobrescritos manejarán la lógica según el esquema
try:
    admin.site.register(TelegramChat, TenantTelegramChatAdmin)
except admin.sites.AlreadyRegistered:
    pass

try:
    admin.site.register(TelegramMessage, TenantTelegramMessageAdmin)
except admin.sites.AlreadyRegistered:
    pass
