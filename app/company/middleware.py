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
        self._admin_configured = {}  # Cache para evitar reconfigurar

    def __call__(self, request):
        # Configurar admin según el esquema antes de procesar la request
        self._configure_admin_for_schema()
        
        response = self.get_response(request)
        return response

    def _configure_admin_for_schema(self):
        """Configura el admin según el esquema activo"""
        schema_name = connection.schema_name
        
        # Solo configurar una vez por esquema
        if schema_name in self._admin_configured:
            return
            
        try:
            if schema_name == 'public':
                self._configure_public_admin()
            else:
                self._configure_tenant_admin()
                
            self._admin_configured[schema_name] = True
            
        except Exception:
            # Si hay error, no bloquear la aplicación
            pass

    def _configure_public_admin(self):
        """Configura admin para esquema público (super admin)"""
        from .models import Company, Domain
        from .admin import CompanyAdmin, DomainAdmin
        
        # Registrar modelos de tenant management
        try:
            admin.site.register(Company, CompanyAdmin)
        except admin.sites.AlreadyRegistered:
            pass
            
        try:
            admin.site.register(Domain, DomainAdmin)
        except admin.sites.AlreadyRegistered:
            pass
            
        # Registrar cross-tenant admin
        from .super_admin import register_cross_tenant_admin
        register_cross_tenant_admin()

    def _configure_tenant_admin(self):
        """Configura admin para esquemas de tenant (sin gestión de tenants)"""
        from .models import Company, Domain
        
        # Desregistrar modelos que no deben aparecer en tenants
        try:
            if Company in admin.site._registry:
                admin.site.unregister(Company)
        except:
            pass
            
        try:
            if Domain in admin.site._registry:
                admin.site.unregister(Domain)
        except:
            pass
            
        # Usar el mismo template pero el context processor manejará las diferencias
        # admin.site.index_template = 'admin/index.html'  # Por defecto
        
        # Configurar títulos específicos del tenant
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