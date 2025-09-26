"""
Context processors para agregar información del esquema a los templates
"""
from django.db import connection


def schema_context(request):
    """
    Agrega información del esquema actual al contexto de los templates
    """
    try:
        schema_name = getattr(connection, 'schema_name', 'public')
        is_public = schema_name == 'public'
        
        context = {
            'is_public_schema': is_public,
            'is_tenant_schema': not is_public,
            'current_schema': schema_name,
        }
        
        # Si estamos en un tenant, agregar información de la empresa
        if not is_public:
            try:
                tenant = getattr(connection, 'tenant', None)
                if tenant:
                    context['current_tenant'] = tenant
                    context['tenant_name'] = getattr(tenant, 'name', 'Empresa')
            except:
                pass
                
        return context
        
    except Exception:
        # Si hay algún error, asumir que estamos en público
        return {
            'is_public_schema': True,
            'is_tenant_schema': False,
            'current_schema': 'public',
        }