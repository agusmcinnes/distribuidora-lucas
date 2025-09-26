from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.forms import ModelForm, CharField, EmailField, PasswordInput
from django.core.exceptions import ValidationError
from django_tenants.utils import tenant_context, get_tenant_model
from .models import Company, Domain


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
        "get_tenant_emails_count",
        "get_telegram_bots_count",
        "is_active_display",
        "created_at",
    ]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "schema_name"]
    readonly_fields = ["created_at", "updated_at", "get_tenant_users_count", "get_tenant_emails_count", "get_telegram_bots_count"]
    inlines = [DomainInline]
    
    def get_fieldsets(self, request, obj=None):
        if obj:  # Editando empresa existente
            return (
                ("Información Básica", {"fields": ("name", "schema_name", "is_active")}),
                (
                    "Estadísticas del Tenant",
                    {
                        "fields": ("get_tenant_users_count", "get_tenant_emails_count", "get_telegram_bots_count"),
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
    
    def get_tenant_emails_count(self, obj):
        """Obtener cantidad de emails por tenant"""
        if obj.schema_name == 'public':
            return "N/A (Esquema público)"
        try:
            with tenant_context(obj):
                from emails.models import ReceivedEmail
                return ReceivedEmail.objects.count()
        except:
            return 0
    get_tenant_emails_count.short_description = "📧 Emails"
    
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


# Registro condicional de admins - solo en esquema público
def register_public_schema_admin():
    """Registra los admins solo cuando estamos en el esquema público"""
    from django.db import connection
    
    if connection.schema_name == 'public':
        try:
            admin.site.register(Company, CompanyAdmin)
            admin.site.register(Domain, DomainAdmin)
        except admin.sites.AlreadyRegistered:
            pass
