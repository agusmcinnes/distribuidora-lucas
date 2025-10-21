from django.db import models
from django_tenants.models import TenantMixin, DomainMixin


class Company(TenantMixin):
    """
    Modelo que representa una empresa distribuidora.
    """

    name = models.CharField(
        max_length=200,
        verbose_name="Nombre de la empresa",
        help_text="Nombre completo de la empresa distribuidora",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Última actualización"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
        help_text="Indica si la empresa está activa en el sistema",
    )

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_active_users_count(self):
        """
        Retorna el número de usuarios activos de la empresa.
        NOTA: No se puede usar self.users directamente en esquema público
        porque es una relación cross-schema.
        """
        from django_tenants.utils import tenant_context
        from django.db import connection

        if self.schema_name == 'public':
            return 0

        try:
            with tenant_context(self):
                from user.models import User
                return User.objects.filter(is_active=True).count()
        except Exception:
            return 0

    get_active_users_count.short_description = "Usuarios activos"


class Domain(DomainMixin):
    """
    Dominios asociados a cada tenant (empresa)
    """
    pass
