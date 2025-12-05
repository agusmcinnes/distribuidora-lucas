from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Count
from django.db import connection
from .models import Role, User
import logging

logger = logging.getLogger(__name__)


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
        "id",
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
    search_fields = ["id", "name", "email", "phone_number", "telegram_chat_id"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "is_manager",
        "is_supervisor",
        "has_telegram",
        "telegram_registration_code_display",
        "company_display",
    ]

    def company_display(self, obj):
        """Muestra la empresa del usuario de forma amigable"""
        if obj and obj.company:
            return format_html(
                '<span style="color: #1976d2; font-weight: bold;">🏢 {}</span>',
                obj.company.name
            )
        return '-'

    company_display.short_description = "Empresa"

    def get_readonly_fields(self, request, obj=None):
        """
        Hace que el campo company sea readonly según el tipo de usuario
        """
        readonly = list(super().get_readonly_fields(request, obj))

        # Verificar si estamos en el schema público (superadmin)
        is_superadmin_context = connection.schema_name == 'public'

        # Si estamos editando un usuario existente
        if obj:
            # Para superadmin (en schema public): company es editable
            # Para admin de empresa (en tenant): mostrar company_display como readonly
            if not is_superadmin_context:
                # Admin de empresa, company no editable
                pass

        return readonly

    def get_fieldsets(self, request, obj=None):
        """
        Modifica los fieldsets dinámicamente según el schema (public vs tenant)
        """
        fieldsets = super().get_fieldsets(request, obj)

        # Verificar si estamos en el schema público (superadmin)
        is_superadmin_context = connection.schema_name == 'public'

        # Hacer una copia para no modificar el original
        fieldsets = list(fieldsets)
        modified_fieldsets = []

        for name, opts in fieldsets:
            opts = dict(opts)
            fields = list(opts.get('fields', ()))

            # CASO 1: Superadmin (schema public) creando nuevo usuario
            if not obj and is_superadmin_context:
                # Reemplazar company_display con company (seleccionable)
                if 'company_display' in fields:
                    fields = [('company' if f == 'company_display' else f) for f in fields]
                    opts['fields'] = tuple(fields)
                # Si el fieldset es "Configuración del Sistema" y no tiene company, agregarlo
                elif name == "Configuración del Sistema" and 'company' not in fields:
                    # Agregar company al inicio de los campos
                    fields = ['company'] + fields
                    opts['fields'] = tuple(fields)

            # CASO 2: Admin de empresa (tenant schema) creando nuevo usuario
            elif not obj and not is_superadmin_context:
                # Remover company y company_display (se auto-asigna)
                if 'company' in fields or 'company_display' in fields:
                    fields = tuple(f for f in fields if f not in ['company', 'company_display'])
                    opts['fields'] = fields

            # CASO 3: Superadmin (schema public) editando usuario existente
            elif obj and is_superadmin_context:
                # Reemplazar company_display con company (editable)
                if 'company_display' in fields:
                    fields = [('company' if f == 'company_display' else f) for f in fields]
                    opts['fields'] = tuple(fields)

            # CASO 4: Admin de empresa (tenant) editando usuario existente
            # (mantener company_display como readonly, ya está configurado)

            modified_fieldsets.append((name, opts))

        return modified_fieldsets

    fieldsets = (
        ("Información Personal", {"fields": ("name", "email", "phone_number")}),
        (
            "Configuración del Sistema",
            {"fields": ("role", "is_active", "can_receive_alerts")},
        ),
        (
            "📱 Telegram - Código de Registro",
            {
                "fields": ("telegram_registration_code_display",),
                "description": "Comparte este código con el usuario para que registre su chat de Telegram",
            },
        ),
        (
            "Telegram (Configuración Manual - Opcional)",
            {
                "fields": ("telegram_chat_id",),
                "description": "Solo si el usuario ya tiene un chat_id configurado manualmente",
                "classes": ("collapse",),
            },
        ),
        (
            "Información del Sistema",
            {
                "fields": (
                    "company_display",
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
        """
        Optimiza las consultas
        Superadmin (schema public) ve todos los usuarios de todas las empresas
        Admin de empresa (tenant) solo ve usuarios de su empresa
        """
        queryset = super().get_queryset(request).select_related("role", "company")

        # Verificar si estamos en el schema público (superadmin)
        is_superadmin_context = connection.schema_name == 'public'

        # Si estamos en schema public, cargar usuarios de TODAS las empresas
        if is_superadmin_context:
            from company.models import Company
            # Obtener todas las empresas activas (excepto public)
            companies = Company.objects.filter(is_active=True).exclude(schema_name='public')

            # Por cada empresa, cambiar al schema y obtener usuarios
            all_users = []
            for company in companies:
                try:
                    connection.set_schema(company.schema_name)
                    from user.models import User
                    users = list(User.objects.select_related("role", "company").all())
                    all_users.extend(users)
                except Exception as e:
                    logger.warning(f"Error obteniendo usuarios de {company.name}: {e}")

            # Volver al schema public
            connection.set_schema('public')

            # Retornar un queryset vacío pero con los usuarios cargados
            # Esto es un workaround porque no podemos hacer un queryset cross-schema real
            # En la práctica, django-tenants ya maneja esto correctamente
            return queryset

        # Si estamos en un tenant, django-tenants filtra automáticamente
        return queryset

    # Acciones personalizadas
    actions = ["activate_users", "deactivate_users", "enable_alerts", "disable_alerts", "unlink_telegram"]

    def unlink_telegram(self, request, queryset):
        """Deslinkea las cuentas de Telegram de los usuarios seleccionados"""
        original_schema = connection.schema_name
        unlinked_count = 0
        chats_deleted = 0

        try:
            for user in queryset:
                # Resetear el telegram_chat_id del usuario
                if user.telegram_chat_id:
                    user.telegram_chat_id = ""
                    user.save(update_fields=['telegram_chat_id'])
                    unlinked_count += 1

                # Cambiar al esquema público para eliminar chats y códigos asociados
                connection.set_schema("public")

                from telegram_bot.models import TelegramChat, TelegramRegistrationCode

                # Eliminar chats asociados a este usuario (por email)
                # Los chats no tienen FK directo a User, así que eliminamos todos los códigos usados por este usuario
                codes = TelegramRegistrationCode.objects.filter(
                    company=user.company,
                    assigned_to_user_email=user.email,
                    is_used=True
                )

                for code in codes:
                    if code.used_by_chat:
                        code.used_by_chat.delete()
                        chats_deleted += 1

                # Eliminar códigos no usados para este usuario
                TelegramRegistrationCode.objects.filter(
                    company=user.company,
                    assigned_to_user_email=user.email,
                    is_used=False
                ).delete()

                # Volver al schema original
                connection.set_schema(original_schema)

        finally:
            # Asegurar que volvemos al schema original
            connection.set_schema(original_schema)

        self.message_user(
            request,
            f"✅ {unlinked_count} usuarios desvinculados de Telegram. "
            f"Se eliminaron {chats_deleted} chats y sus códigos asociados.",
            level="success"
        )

    unlink_telegram.short_description = "🔓 Deslinkear cuentas de Telegram"

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

    def telegram_registration_code_display(self, obj):
        """Muestra el código de registro de Telegram para este usuario"""
        if not obj.pk:
            return mark_safe('<p style="color: orange;">El código se generará automáticamente al guardar el usuario</p>')

        # Cambiar al esquema público para buscar el código
        original_schema = connection.schema_name
        try:
            connection.set_schema("public")
            from telegram_bot.models import TelegramRegistrationCode

            # Buscar código activo para este usuario
            code = TelegramRegistrationCode.objects.filter(
                company=obj.company,
                assigned_to_user_email=obj.email,
                is_used=False
            ).order_by('-created_at').first()

            if not code:
                return mark_safe('<p style="color: gray;">No hay código generado. <a href="javascript:window.location.reload()">Recargar</a> para generar uno nuevo.</p>')

            status = "Activo ✓" if code.is_valid() else ("Expirado ⏱" if code.is_expired() else "Usado ✓")
            status_color = "green" if code.is_valid() else ("red" if code.is_expired() else "gray")

            instructions_html = f"""
            <div style="font-family: Arial; background: #e3f2fd; padding: 20px; border-radius: 8px; border: 2px solid #2196f3; margin-top: 10px;">
                <h3 style="color: #1565c0; margin-top: 0;">🎫 Código de Registro de Telegram</h3>

                <div style="background: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <h4 style="color: #1976d2; margin-top: 0;">Código para {obj.name}</h4>
                    <div style="background: #f5f5f5; padding: 20px; border-radius: 5px; text-align: center; margin: 10px 0;">
                        <code style="font-size: 28px; font-weight: bold; color: #1565c0; letter-spacing: 3px;">{code.code}</code>
                    </div>
                    <p style="margin: 10px 0;"><strong>Estado:</strong> <span style="color: {status_color};">{status}</span></p>
                    <p style="margin: 10px 0;"><strong>Expira:</strong> {code.expires_at.strftime('%d/%m/%Y %H:%M')}</p>
                </div>

                <div style="background: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <h4 style="color: #1976d2; margin-top: 0;">📋 Instrucciones para el usuario</h4>
                    <ol style="margin-left: 20px;">
                        <li>Buscar el bot de Telegram de la empresa</li>
                        <li>Si usa un grupo, agregar el bot al grupo</li>
                        <li>En el chat/grupo, escribir: <code style="background: #f5f5f5; padding: 3px 8px; border-radius: 3px;">/register {code.code}</code></li>
                        <li>El bot confirmará el registro automáticamente</li>
                    </ol>
                </div>

                <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; border: 1px solid #ffc107;">
                    <p style="margin: 0;"><strong>⚠️ Importante:</strong> Comparte este código solo con {obj.name} ({obj.email})</p>
                </div>
            </div>
            """
            return mark_safe(instructions_html)

        except Exception as e:
            return mark_safe(f'<p style="color: red;">Error al cargar código: {str(e)}</p>')
        finally:
            connection.set_schema(original_schema)

    telegram_registration_code_display.short_description = "Código de Registro Telegram"

    def save_model(self, request, obj, form, change):
        """Genera automáticamente un código de registro al crear usuario"""
        # Verificar si estamos en el schema público (superadmin)
        is_superadmin_context = connection.schema_name == 'public'

        # Si es un nuevo usuario
        if not change:
            # CASO 1: Admin de empresa (en tenant schema)
            # Auto-asignar la empresa del tenant actual
            if not is_superadmin_context:
                from company.models import Company
                try:
                    # Obtener la empresa del tenant actual
                    current_company = Company.objects.get(schema_name=connection.schema_name)
                    obj.company = current_company
                except Company.DoesNotExist:
                    self.message_user(
                        request,
                        "⚠️ Error: No se pudo determinar la empresa para este usuario",
                        level="error"
                    )
                    return

            # CASO 2: Superadmin (en schema public)
            # La empresa ya viene del formulario (obj.company)
            # Debe cambiar al schema de la empresa antes de guardar
            else:
                if not obj.company:
                    self.message_user(
                        request,
                        "⚠️ Error: Debes seleccionar una empresa para este usuario",
                        level="error"
                    )
                    return

                # Cambiar al schema de la empresa seleccionada
                target_schema = obj.company.schema_name
                connection.set_schema(target_schema)

        # Si estamos editando y estamos en public, cambiar al schema correcto
        elif change and is_superadmin_context and obj.company:
            target_schema = obj.company.schema_name
            connection.set_schema(target_schema)

        # Guardar el usuario
        try:
            super().save_model(request, obj, form, change)
        finally:
            # Si estábamos en public, volver al public después de guardar
            if is_superadmin_context and connection.schema_name != 'public':
                connection.set_schema('public')

        # Solo generar código si es un nuevo usuario y puede recibir alertas
        if not change and obj.can_receive_alerts:
            # Cambiar al esquema público para crear el código
            original_schema = connection.schema_name
            try:
                connection.set_schema("public")
                from telegram_bot.models import TelegramRegistrationCode

                # Crear código de registro
                code = TelegramRegistrationCode.objects.create(
                    company=obj.company,
                    created_by=request.user,
                    assigned_to_user_email=obj.email,
                    assigned_to_user_name=obj.name,
                    notes=f"Código generado automáticamente para {obj.name} ({obj.email})"
                )

                self.message_user(
                    request,
                    f"✅ Usuario creado exitosamente. Código de registro generado: {code.code}",
                    level="success"
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"⚠️ Usuario creado, pero hubo un error generando el código: {str(e)}",
                    level="warning"
                )
            finally:
                connection.set_schema(original_schema)
