"""
URLs para el esquema público (super admin)
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.http import JsonResponse
from company.views import cross_tenant_dashboard, cross_tenant_users_api, custom_admin_index

def redirect_to_admin(request):
    """Redirige la raíz al admin"""
    return redirect('/admin/')

def health_check(request):
    """Health check endpoint for load balancers and monitoring"""
    return JsonResponse({'status': 'ok'})

urlpatterns = [
    path('', redirect_to_admin, name='public_home'),
    path('health/', health_check, name='health_check'),
    path('cross-tenant-dashboard/', cross_tenant_dashboard, name='cross_tenant_dashboard'),
    path('api/cross-tenant-users/', cross_tenant_users_api, name='cross_tenant_users_api'),
    path('admin/', admin.site.urls),
]

# Configuración del admin público
admin.site.site_header = "🏢 Distribuidora Lucas - Super Admin"
admin.site.site_title = "Super Admin"
admin.site.index_title = "Panel de Super Administración - Ver Todas las Empresas"

# Personalizar la vista del admin index solo para el esquema público
admin.site.index_template = 'admin/index.html'