"""
URLs para tenants (empresas específicas)
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.http import JsonResponse


def redirect_to_admin(request):
    """Redirige la raíz al admin"""
    return redirect("/admin/")


def health_check(request):
    """Health check endpoint for load balancers and monitoring"""
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path("", redirect_to_admin, name="home"),
    path("health/", health_check, name="health_check"),
    path("admin/", admin.site.urls),
    path("telegram/", include("telegram_bot.urls")),
]
