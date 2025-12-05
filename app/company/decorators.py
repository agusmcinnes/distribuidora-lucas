"""
Decoradores para control de acceso basado en esquemas de tenant
"""
from functools import wraps
from django.http import Http404
from django.db import connection
from django.contrib.auth.decorators import user_passes_test


def public_schema_required(view_func):
    """
    Decorador que requiere que la vista sea accedida desde el esquema público.
    Usado para vistas de super admin que no deben estar disponibles en tenants.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if connection.schema_name != 'public':
            raise Http404("Esta página no está disponible en el contexto de empresa.")
        return view_func(request, *args, **kwargs)
    return wrapper


def tenant_schema_required(view_func):
    """
    Decorador que requiere que la vista sea accedida desde un esquema de tenant.
    Usado para vistas específicas de empresa.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if connection.schema_name == 'public':
            raise Http404("Esta página solo está disponible en el contexto de empresa.")
        return view_func(request, *args, **kwargs)
    return wrapper


def superuser_and_public_schema_required(view_func):
    """
    Decorador que requiere superusuario Y esquema público.
    Para funcionalidades de super admin.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if connection.schema_name != 'public':
            raise Http404("Esta página no está disponible en el contexto de empresa.")
        if not request.user.is_authenticated or not request.user.is_superuser:
            raise Http404("Acceso denegado.")
        return view_func(request, *args, **kwargs)
    return wrapper


def is_superuser_in_public():
    """
    Función para usar con user_passes_test que verifica superusuario en esquema público
    """
    def test_func(user):
        return (
            connection.schema_name == 'public' and 
            user.is_authenticated and 
            user.is_superuser
        )
    return test_func