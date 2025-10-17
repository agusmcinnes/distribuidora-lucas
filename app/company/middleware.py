"""
Middleware para configurar el admin según el esquema activo (público vs tenant)
"""
from django.db import connection
from django.contrib import admin


class TenantAdminMiddleware:
    """
    Middleware que configura el admin según si estamos en esquema público o tenant
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Configurar títulos del admin dinámicamente según el esquema
        self._set_admin_titles()

        response = self.get_response(request)
        return response

    def _set_admin_titles(self):
        """Configura los títulos del admin según el esquema activo"""
        try:
            schema_name = connection.schema_name

            if schema_name == 'public':
                admin.site.site_header = "🏢 Distribuidora Lucas - Super Admin"
                admin.site.site_title = "Super Admin"
                admin.site.index_title = "Panel de Super Administración - Ver Todas las Empresas"
            else:
                # Obtener nombre del tenant
                try:
                    tenant = connection.tenant
                    company_name = tenant.name if hasattr(tenant, 'name') else "Empresa"
                    admin.site.site_header = f"🏢 {company_name} - Panel de Administración"
                    admin.site.site_title = f"{company_name} Admin"
                    admin.site.index_title = "Panel de Gestión Empresarial"
                except:
                    admin.site.site_header = "🏢 Panel de Administración"
                    admin.site.site_title = "Admin"
                    admin.site.index_title = "Panel de Gestión"
        except:
            # Default si hay error
            admin.site.site_header = "🏢 Panel de Administración"
            admin.site.site_title = "Admin"
            admin.site.index_title = "Panel de Gestión"