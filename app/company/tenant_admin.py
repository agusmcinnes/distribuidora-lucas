"""
Admin configuration específica para esquemas de tenant.
Solo incluye funcionalidades relevantes para cada empresa individual.
"""
from django.contrib import admin
from django.db import connection


def register_tenant_admin():
    """
    Registra admins específicos para tenants.
    NO incluye gestión de Company/Domain ya que eso es del super admin.
    """
    if connection.schema_name != 'public':
        # Aquí podríamos registrar admins específicos para tenants
        # si necesitáramos funcionalidades especiales solo para empresas
        pass


def unregister_tenant_models():
    """
    Desregistra modelos que no deben aparecer en el admin de tenants.
    """
    if connection.schema_name != 'public':
        try:
            # Asegurarse de que Company y Domain no estén registrados en tenants
            from .models import Company, Domain
            
            if Company in admin.site._registry:
                admin.site.unregister(Company)
            if Domain in admin.site._registry:
                admin.site.unregister(Domain)
                
        except Exception:
            # Si los modelos no están registrados, no hay problema
            pass