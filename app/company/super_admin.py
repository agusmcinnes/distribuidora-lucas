"""
Admin personalizado para super administrador con acceso cross-tenant
"""
from django.contrib import admin
from django.utils.html import format_html
from django_tenants.utils import tenant_context
from .models import Company


class CrossTenantUserAdmin(admin.ModelAdmin):
    """Admin para ver usuarios de todos los tenants"""
    list_display = ['username', 'email', 'first_name', 'last_name', 'tenant_name', 'is_active', 'is_staff']
    list_filter = ['is_active', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    readonly_fields = ['username', 'email', 'first_name', 'last_name', 'tenant_name', 'date_joined']

    def get_queryset(self, request):
        """Obtener usuarios de todos los tenants"""
        users = []
        for company in Company.objects.filter(is_active=True).exclude(schema_name='public'):
            try:
                with tenant_context(company):
                    from django.contrib.auth.models import User
                    tenant_users = list(User.objects.all())
                    for user in tenant_users:
                        user.tenant_name = company.name
                        users.append(user)
            except:
                continue
        return users

    def tenant_name(self, obj):
        return getattr(obj, 'tenant_name', 'N/A')
    tenant_name.short_description = '🏢 Empresa'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CrossTenantTelegramBotAdmin(admin.ModelAdmin):
    """Admin para ver bots de Telegram de todos los tenants"""
    list_display = ['bot_name', 'tenant_name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['bot_name']
    readonly_fields = ['bot_name', 'bot_token', 'tenant_name', 'created_at']

    def get_queryset(self, request):
        """Obtener bots de todos los tenants"""
        bots = []
        for company in Company.objects.filter(is_active=True).exclude(schema_name='public'):
            try:
                with tenant_context(company):
                    from telegram_bot.models import TelegramConfig
                    tenant_bots = list(TelegramConfig.objects.all())
                    for bot in tenant_bots:
                        bot.tenant_name = company.name
                        bots.append(bot)
            except:
                continue
        return bots

    def tenant_name(self, obj):
        return getattr(obj, 'tenant_name', 'N/A')
    tenant_name.short_description = '🏢 Empresa'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# Crear modelos proxy para registrar en el admin
class UserProxy:
    class Meta:
        verbose_name = "👥 Usuario de Todas las Empresas"
        verbose_name_plural = "👥 Usuarios de Todas las Empresas"


class TelegramBotProxy:
    class Meta:
        verbose_name = "🤖 Bot de Todas las Empresas"
        verbose_name_plural = "🤖 Bots de Todas las Empresas"


# Registrar en el admin solo cuando estamos en el esquema público
def register_cross_tenant_admin():
    from django.db import connection
    if connection.schema_name == 'public':
        try:
            admin.site.register(UserProxy, CrossTenantUserAdmin)
            admin.site.register(TelegramBotProxy, CrossTenantTelegramBotAdmin)
        except admin.sites.AlreadyRegistered:
            pass
