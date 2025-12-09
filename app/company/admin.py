from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.hashers import make_password
from django.db import transaction, connection
from django.forms import ModelForm, CharField, EmailField, PasswordInput
from django.core.exceptions import ValidationError
from django_tenants.utils import tenant_context, get_tenant_model
from django.urls import reverse
from .models import Company, Domain
import logging

logger = logging.getLogger(__name__)


class DomainInline(admin.TabularInline):
    model = Domain
    extra = 1
    fields = ['domain', 'is_primary']
    help_text = {
        'domain': 'Formato: empresa.localhost o empresa.tudominio.com'
    }


class CompanyCreateForm(ModelForm):
    """
    Formulario personalizado para crear empresa con usuario administrador
    """
    admin_username = CharField(
        max_length=150,
        required=True,
        help_text="Usuario administrador para la empresa"
    )
    admin_email = EmailField(
        required=True,
        help_text="Email del administrador"
    )
    admin_password = CharField(
        widget=PasswordInput,
        required=True,
        min_length=8,
        help_text="Contraseña para el administrador (mínimo 8 caracteres)"
    )
    admin_password_confirm = CharField(
        widget=PasswordInput,
        required=True,
        help_text="Confirmar contraseña"
    )
    domain_name = CharField(
        max_length=253,
        required=True,
        help_text="Dominio para acceder (ej: empresa.localhost)"
    )

    class Meta:
        model = Company
        fields = ['name', 'schema_name', 'is_active']
        help_texts = {
            'schema_name': 'Nombre del esquema PostgreSQL (solo letras, números y guiones bajos)'
        }

    def clean_schema_name(self):
        schema_name = self.cleaned_data.get('schema_name')
        if schema_name:
            # Validar que el schema_name no esté en uso
            if Company.objects.filter(schema_name=schema_name).exists():
                raise ValidationError(f"El schema '{schema_name}' ya está en uso.")
            # Validar formato del schema name
            if not schema_name.replace('_', '').replace('-', '').isalnum():
                raise ValidationError("El schema solo puede contener letras, números, guiones y guiones bajos.")
        return schema_name

    def clean_domain_name(self):
        domain = self.cleaned_data.get('domain_name')
        if domain:
            if Domain.objects.filter(domain=domain).exists():
                raise ValidationError(f"El dominio '{domain}' ya está en uso.")
        return domain

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('admin_password')
        password_confirm = cleaned_data.get('admin_password_confirm')
        
        if password and password_confirm:
            if password != password_confirm:
                raise ValidationError("Las contraseñas no coinciden.")
        
        return cleaned_data


class CompanyAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Company con acceso cross-tenant.
    """

    form = CompanyCreateForm
    list_display = [
        "name",
        "schema_name",
        "get_domain_display",
        "get_tenant_users_count",
        "get_telegram_bots_count",
        "is_active_display",
        "created_at",
    ]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "schema_name"]
    readonly_fields = ["created_at", "updated_at", "get_tenant_users_count", "get_telegram_bots_count", "manage_users_display"]
    inlines = [DomainInline]
    actions = ['create_user_for_companies']
    
    def get_fieldsets(self, request, obj=None):
        if obj:  # Editando empresa existente
            return (
                ("Información Básica", {"fields": ("name", "schema_name", "is_active")}),
                (
                    "👥 Gestión de Usuarios",
                    {
                        "fields": ("manage_users_display",),
                        "description": "Gestiona los usuarios de esta empresa y sus accesos a Telegram"
                    },
                ),
                (
                    "Estadísticas del Tenant",
                    {
                        "fields": ("get_tenant_users_count", "get_telegram_bots_count"),
                        "classes": ("collapse",),
                    },
                ),
                (
                    "Información del Sistema",
                    {
                        "fields": ("created_at", "updated_at"),
                        "classes": ("collapse",),
                    },
                ),
            )
        else:  # Creando nueva empresa
            return (
                ("Información de la Empresa", {
                    "fields": ("name", "schema_name", "is_active"),
                    "description": "Información básica de la empresa distribuidora"
                }),
                ("Dominio de Acceso", {
                    "fields": ("domain_name",),
                    "description": "Dominio para acceder al panel de la empresa"
                }),
                ("Usuario Administrador", {
                    "fields": ("admin_username", "admin_email", "admin_password", "admin_password_confirm"),
                    "description": "Credenciales del administrador principal de la empresa"
                }),
            )

    def get_tenant_users_count(self, obj):
        """Obtener cantidad de usuarios por tenant"""
        if obj.schema_name == 'public':
            return "N/A (Esquema público)"
        try:
            with tenant_context(obj):
                from django.contrib.auth.models import User
                return User.objects.count()
        except:
            return 0
    get_tenant_users_count.short_description = "👥 Usuarios"

    def get_telegram_bots_count(self, obj):
        """Obtener cantidad de bots de Telegram por tenant"""
        if obj.schema_name == 'public':
            return "N/A (Esquema público)"
        try:
            with tenant_context(obj):
                from telegram_bot.models import TelegramConfig
                return TelegramConfig.objects.count()
        except:
            return 0
    get_telegram_bots_count.short_description = "🤖 Bots Telegram"

    def manage_users_display(self, obj):
        """Muestra interfaz para gestionar usuarios de la empresa"""
        if obj.schema_name == 'public':
            return mark_safe('<p style="color: gray;">No aplicable para esquema público</p>')

        original_schema = connection.schema_name
        try:
            # Cambiar al schema de la empresa
            connection.set_schema(obj.schema_name)

            from user.models import User, Role

            # Obtener todos los usuarios
            users = User.objects.select_related('role').all()

            if not users.exists():
                html = '''
                <div style="font-family: Arial; background: #fff3cd; padding: 20px; border-radius: 8px; border: 2px solid #ffc107;">
                    <h3 style="color: #856404; margin-top: 0;">⚠️ No hay usuarios en esta empresa</h3>
                    <p>Utiliza el formulario de abajo para crear el primer usuario.</p>
                </div>
                '''
            else:
                # Construir tabla de usuarios
                rows = []
                for user in users:
                    # Obtener código de telegram
                    telegram_code = self._get_telegram_code_for_user(user, obj)
                    telegram_status = self._get_telegram_status(user, obj)

                    rows.append(f'''
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{user.id}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>{user.name}</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{user.email}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{user.role.get_type_display()}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{telegram_status}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">{telegram_code}</td>
                        <td style="padding: 10px; border-bottom: 1px solid #ddd;">
                            {'<span style="color: green;">✓ Activo</span>' if user.is_active else '<span style="color: red;">✗ Inactivo</span>'}
                        </td>
                    </tr>
                    ''')

                html = f'''
                <div style="font-family: Arial;">
                    <h3 style="color: #1976d2; margin-top: 0;">👥 Usuarios de {obj.name} ({len(users)} total)</h3>
                    <table style="width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <thead style="background: #1976d2; color: white;">
                            <tr>
                                <th style="padding: 12px; text-align: left;">ID</th>
                                <th style="padding: 12px; text-align: left;">Nombre</th>
                                <th style="padding: 12px; text-align: left;">Email</th>
                                <th style="padding: 12px; text-align: left;">Rol</th>
                                <th style="padding: 12px; text-align: left;">Telegram</th>
                                <th style="padding: 12px; text-align: left;">Código Registro</th>
                                <th style="padding: 12px; text-align: left;">Estado</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(rows)}
                        </tbody>
                    </table>
                </div>
                '''

            # Agregar formulario para crear nuevo usuario
            # Obtener roles disponibles
            roles = Role.objects.all()
            role_options = ''.join([f'<option value="{role.type}">{role.get_type_display()}</option>' for role in roles])

            html += f'''
            <div style="font-family: Arial; background: #e3f2fd; padding: 20px; border-radius: 8px; border: 2px solid #2196f3; margin-top: 20px;">
                <h3 style="color: #1565c0; margin-top: 0;">➕ Crear Nuevo Usuario</h3>
                <form method="post" style="background: white; padding: 20px; border-radius: 5px;">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{self._get_csrf_token()}">
                    <input type="hidden" name="action" value="create_user_for_company">
                    <input type="hidden" name="company_id" value="{obj.id}">

                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; font-weight: bold;">Nombre completo:</label>
                        <input type="text" name="user_name" required style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    </div>

                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; font-weight: bold;">Email:</label>
                        <input type="email" name="user_email" required style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    </div>

                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; font-weight: bold;">Teléfono (opcional):</label>
                        <input type="text" name="user_phone" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    </div>

                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; font-weight: bold;">Rol:</label>
                        <select name="user_role" required style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                            {role_options}
                        </select>
                    </div>

                    <div style="margin-bottom: 15px;">
                        <label style="display: inline-block; margin-right: 10px;">
                            <input type="checkbox" name="user_can_receive_alerts" checked value="1">
                            Puede recibir alertas
                        </label>
                    </div>

                    <button type="submit" style="background: #2196f3; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">
                        ➕ Crear Usuario y Generar Código Telegram
                    </button>
                </form>
            </div>
            '''

            return mark_safe(html)

        except Exception as e:
            logger.error(f"Error mostrando usuarios: {e}", exc_info=True)
            return mark_safe(f'<p style="color: red;">Error: {str(e)}</p>')
        finally:
            connection.set_schema(original_schema)

    manage_users_display.short_description = "Gestión de Usuarios"

    def _get_csrf_token(self):
        """Helper para obtener el CSRF token del request actual"""
        from django.middleware.csrf import get_token
        return get_token(self._current_request)

    def _get_telegram_code_for_user(self, user, company):
        """Obtiene el código de telegram activo para un usuario"""
        original_schema = connection.schema_name
        try:
            connection.set_schema('public')
            from telegram_bot.models import TelegramRegistrationCode

            code = TelegramRegistrationCode.objects.filter(
                company=company,
                assigned_to_user_email=user.email,
                is_used=False
            ).order_by('-created_at').first()

            if code and code.is_valid():
                return f'<code style="background: #f5f5f5; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{code.code}</code>'
            elif code and code.is_expired():
                return '<span style="color: orange;">Código expirado</span>'
            elif code and code.is_used:
                return '<span style="color: gray;">Código usado</span>'
            else:
                return '<span style="color: gray;">Sin código</span>'
        except Exception as e:
            return f'<span style="color: red;">Error</span>'
        finally:
            connection.set_schema(original_schema)

    def _get_telegram_status(self, user, company):
        """Obtiene el estado de telegram del usuario"""
        original_schema = connection.schema_name
        try:
            connection.set_schema('public')
            from telegram_bot.models import TelegramChat, TelegramRegistrationCode

            # Buscar si tiene chat vinculado
            code = TelegramRegistrationCode.objects.filter(
                company=company,
                assigned_to_user_email=user.email,
                is_used=True
            ).first()

            if code and code.used_by_chat:
                return f'<span style="color: green;">✓ Vinculado</span>'
            elif user.telegram_chat_id:
                return f'<span style="color: green;">✓ Manual</span>'
            else:
                return '<span style="color: gray;">✗ No vinculado</span>'
        except:
            return '<span style="color: gray;">-</span>'
        finally:
            connection.set_schema(original_schema)

    def is_active_display(self, obj):
        """Muestra el estado activo con colores"""
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Activa</span>')
        return format_html('<span style="color: red;">✗ Inactiva</span>')

    is_active_display.short_description = "Estado"

    def get_domain_display(self, obj):
        """Muestra el dominio principal de la empresa"""
        domain = obj.domains.filter(is_primary=True).first()
        if domain:
            return format_html('<a href="http://{}/admin/" target="_blank">{}</a>', domain.domain, domain.domain)
        return "Sin dominio"
    
    get_domain_display.short_description = "Dominio Principal"
    get_domain_display.allow_tags = True

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override para manejar el POST de creación de usuarios"""
        # Guardar request para uso en manage_users_display
        self._current_request = request

        if request.method == 'POST' and request.POST.get('action') == 'create_user_for_company':
            return self._handle_create_user(request, object_id)

        return super().changeform_view(request, object_id, form_url, extra_context)

    def _handle_create_user(self, request, company_id):
        """Maneja la creación de un nuevo usuario para la empresa"""
        from django.http import HttpResponseRedirect
        from django.urls import reverse

        original_schema = connection.schema_name

        try:
            # Obtener la empresa
            company = Company.objects.get(id=company_id)

            # Obtener datos del formulario
            user_name = request.POST.get('user_name')
            user_email = request.POST.get('user_email')
            user_phone = request.POST.get('user_phone', '')
            user_role_type = request.POST.get('user_role')
            user_can_receive_alerts = request.POST.get('user_can_receive_alerts') == '1'

            # Validar datos
            if not user_name or not user_email or not user_role_type:
                self.message_user(
                    request,
                    "❌ Error: Nombre, email y rol son obligatorios",
                    level='error'
                )
                return HttpResponseRedirect(reverse('admin:company_company_change', args=[company_id]))

            # Cambiar al schema de la empresa
            connection.set_schema(company.schema_name)

            from user.models import User, Role

            # Verificar si el email ya existe
            if User.objects.filter(email=user_email).exists():
                self.message_user(
                    request,
                    f"❌ Error: Ya existe un usuario con el email {user_email}",
                    level='error'
                )
                connection.set_schema(original_schema)
                return HttpResponseRedirect(reverse('admin:company_company_change', args=[company_id]))

            # Obtener el rol
            try:
                role = Role.objects.get(type=user_role_type)
            except Role.DoesNotExist:
                self.message_user(
                    request,
                    f"❌ Error: El rol '{user_role_type}' no existe",
                    level='error'
                )
                connection.set_schema(original_schema)
                return HttpResponseRedirect(reverse('admin:company_company_change', args=[company_id]))

            # Crear el usuario
            user = User.objects.create(
                name=user_name,
                email=user_email,
                phone_number=user_phone,
                role=role,
                company=company,
                is_active=True,
                can_receive_alerts=user_can_receive_alerts
            )

            # Volver al schema público
            connection.set_schema('public')

            # Crear código de registro de Telegram si puede recibir alertas
            telegram_code = None
            if user_can_receive_alerts:
                from telegram_bot.models import TelegramRegistrationCode

                telegram_code = TelegramRegistrationCode.objects.create(
                    company=company,
                    created_by=request.user,
                    assigned_to_user_email=user.email,
                    assigned_to_user_name=user.name,
                    notes=f"Código generado automáticamente para {user.name} ({user.email})"
                )

            # Mensaje de éxito
            if telegram_code:
                self.message_user(
                    request,
                    format_html(
                        '✅ Usuario <strong>{}</strong> creado exitosamente!<br/>'
                        '🎫 Código de registro de Telegram: <strong>{}</strong><br/>'
                        '📧 Email: {}',
                        user_name,
                        telegram_code.code,
                        user_email
                    ),
                    level='success'
                )
            else:
                self.message_user(
                    request,
                    format_html(
                        '✅ Usuario <strong>{}</strong> creado exitosamente!<br/>'
                        '📧 Email: {}',
                        user_name,
                        user_email
                    ),
                    level='success'
                )

        except Exception as e:
            logger.error(f"Error creando usuario: {e}", exc_info=True)
            self.message_user(
                request,
                f"❌ Error creando usuario: {str(e)}",
                level='error'
            )
        finally:
            # Asegurar que volvemos al schema público
            connection.set_schema(original_schema)

        # Redirigir de vuelta a la página de la empresa
        return HttpResponseRedirect(reverse('admin:company_company_change', args=[company_id]))

    def has_module_permission(self, request):
        """Solo mostrar en esquema público (superadmin)"""
        return connection.schema_name == "public"

    def get_deleted_objects(self, objs, request):
        """
        Override para evitar que Django intente hacer queries cross-schema
        al verificar objetos relacionados antes de eliminar
        """
        from django.utils.encoding import force_str
        from django.utils.html import format_html

        # Construir la lista de objetos manualmente sin usar collector
        # para evitar queries cross-schema
        perms_needed = set()
        protected = []
        to_delete = []
        model_count = {}

        def format_callback(obj):
            return force_str(obj)

        for obj in objs:
            opts = obj._meta
            verbose_name = opts.verbose_name

            # Información básica de la empresa
            info_items = [f"Empresa: {obj.name}", f"Schema: {obj.schema_name}"]

            # Contar objetos dentro del tenant si es posible
            if obj.schema_name != 'public':
                try:
                    with tenant_context(obj):
                        from user.models import User

                        user_count = User.objects.count()

                        if user_count > 0:
                            model_count["Usuarios"] = user_count
                            info_items.append(f"- {user_count} usuarios")

                except Exception as e:
                    logger.error(f"Error contando objetos del tenant: {e}")

                # Contar objetos en schema público relacionados
                try:
                    from telegram_bot.models import TelegramChat, TelegramMessage, TelegramRegistrationCode

                    chat_count = TelegramChat.objects.filter(company=obj).count()
                    msg_count = TelegramMessage.objects.filter(company=obj).count()
                    code_count = TelegramRegistrationCode.objects.filter(company=obj).count()

                    if chat_count > 0:
                        model_count["Chats de Telegram"] = chat_count
                        info_items.append(f"- {chat_count} chats de Telegram")

                    if msg_count > 0:
                        model_count["Mensajes de Telegram"] = msg_count
                        info_items.append(f"- {msg_count} mensajes de Telegram")

                    if code_count > 0:
                        model_count["Códigos de registro"] = code_count
                        info_items.append(f"- {code_count} códigos de registro")

                except Exception as e:
                    logger.error(f"Error contando objetos de Telegram: {e}")

            # Agregar a la lista
            to_delete.append([
                format_callback(obj),
                info_items
            ])

        return to_delete, model_count, perms_needed, protected

    def delete_model(self, request, obj):
        """
        Override para eliminar correctamente una empresa con su tenant
        """
        if obj.schema_name == 'public':
            self.message_user(
                request,
                "No se puede eliminar el esquema público",
                level='error'
            )
            return

        try:
            user_count = 0
            telegram_chats_count = 0
            telegram_messages_count = 0
            telegram_codes_count = 0

            # Guardar información antes de eliminar
            schema_name = obj.schema_name
            company_name = obj.name
            company_id = obj.id

            # Paso 1: Contar objetos del tenant (si existe)
            original_schema = connection.schema_name
            try:
                connection.set_schema(schema_name)

                from user.models import User

                try:
                    user_count = User.objects.count()
                except Exception as count_error:
                    # El schema puede no existir si hubo un error anterior
                    logger.warning(f"No se pudieron contar objetos del schema {schema_name}: {count_error}")
                    user_count = 0
            finally:
                connection.set_schema(original_schema)

            # Paso 2: Volver al schema público
            connection.set_schema('public')

            # Contar objetos en schema público
            from telegram_bot.models import TelegramChat, TelegramMessage, TelegramRegistrationCode

            telegram_chats_count = TelegramChat.objects.filter(company=obj).count()
            telegram_messages_count = TelegramMessage.objects.filter(company=obj).count()
            telegram_codes_count = TelegramRegistrationCode.objects.filter(company=obj).count()

            # Eliminar objetos de Telegram
            TelegramChat.objects.filter(company=obj).delete()
            TelegramMessage.objects.filter(company=obj).delete()
            TelegramRegistrationCode.objects.filter(company=obj).delete()

            # Eliminar dominios asociados
            Domain.objects.filter(tenant=obj).delete()

            # Paso 3: Eliminar el schema PostgreSQL directamente usando SQL
            from django.db import connection as db_connection
            with db_connection.cursor() as cursor:
                # Eliminar el schema y todo su contenido
                cursor.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
                logger.info(f"Schema {schema_name} eliminado con DROP SCHEMA CASCADE")

            # Paso 4: Eliminar el registro de la empresa usando SQL directo
            # para evitar que Django intente verificar relaciones
            with db_connection.cursor() as cursor:
                cursor.execute(
                    'DELETE FROM company_company WHERE id = %s',
                    [company_id]
                )
                logger.info(f"Registro de empresa {company_id} eliminado")

            self.message_user(
                request,
                f'Empresa "{company_name}" eliminada exitosamente. '
                f'Se eliminaron: {user_count} usuarios, '
                f'{telegram_chats_count} chats de Telegram, {telegram_messages_count} mensajes de Telegram, '
                f'{telegram_codes_count} códigos de registro.',
                level='success'
            )
        except Exception as e:
            logger.error(f"Error eliminando empresa: {str(e)}", exc_info=True)

            self.message_user(
                request,
                f'Error eliminando empresa: {str(e)}',
                level='error'
            )

    def delete_queryset(self, request, queryset):
        """
        Override para eliminar múltiples empresas
        """
        for obj in queryset:
            self.delete_model(request, obj)

    def save_model(self, request, obj, form, change):
        """Guarda la empresa y crea el setup completo si es nueva"""
        if not change:  # Nueva empresa
            with transaction.atomic():
                # Guardar la empresa (esto crea automáticamente el esquema)
                super().save_model(request, obj, form, change)
                
                # Crear el dominio
                domain = Domain.objects.create(
                    domain=form.cleaned_data['domain_name'],
                    tenant=obj,
                    is_primary=True
                )
                
                # Crear el usuario administrador en el tenant
                self._create_admin_user(obj, form.cleaned_data)
                
                # Mostrar mensaje de éxito con información de acceso
                self.message_user(
                    request,
                    format_html(
                        'Empresa "{}" creada exitosamente!<br/>'
                        '<strong>Acceso:</strong> <a href="http://{}/admin/" target="_blank">http://{}/admin/</a><br/>'
                        '<strong>Usuario:</strong> {}<br/>'
                        '<strong>Email:</strong> {}',
                        obj.name,
                        domain.domain,
                        domain.domain,
                        form.cleaned_data['admin_username'],
                        form.cleaned_data['admin_email']
                    )
                )
        else:
            super().save_model(request, obj, form, change)
    
    def _create_admin_user(self, company, form_data):
        """Crea el usuario administrador en el esquema del tenant"""
        with tenant_context(company):
            # Crear usuario de Django Auth
            admin_user = DjangoUser.objects.create(
                username=form_data['admin_username'],
                email=form_data['admin_email'],
                password=make_password(form_data['admin_password']),
                is_staff=True,
                is_superuser=True,
                is_active=True,
                first_name="Administrador",
                last_name=company.name
            )
            
            # Crear roles básicos
            from user.models import Role
            manager_role, _ = Role.objects.get_or_create(
                type='manager',
                defaults={'description': 'Rol de administrador con acceso completo'}
            )
            supervisor_role, _ = Role.objects.get_or_create(
                type='supervisor', 
                defaults={'description': 'Rol de supervisor con acceso limitado'}
            )
            client_role, _ = Role.objects.get_or_create(
                type='client',
                defaults={'description': 'Rol de cliente básico'}
            )
            
            # Crear usuario del sistema personalizado
            from user.models import User
            User.objects.create(
                name=f"Administrador {company.name}",
                email=form_data['admin_email'],
                role=manager_role,
                company=company,
                is_active=True,
                can_receive_alerts=True
            )


class DomainAdmin(admin.ModelAdmin):
    """
    Configuración del admin para dominios.
    """
    list_display = ['domain', 'tenant', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['domain', 'tenant__name']

    def has_module_permission(self, request):
        """Solo mostrar en esquema público (superadmin)"""
        return connection.schema_name == "public"


# Registrar siempre los admins (el middleware se encarga de filtrarlos)
try:
    admin.site.register(Company, CompanyAdmin)
except admin.sites.AlreadyRegistered:
    pass

try:
    admin.site.register(Domain, DomainAdmin)
except admin.sites.AlreadyRegistered:
    pass
