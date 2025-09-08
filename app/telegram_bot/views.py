"""
Vistas básicas para Telegram (solo lo esencial)
"""

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .models import TelegramConfig


@require_GET
def bot_status(request):
    """
    Vista simple para verificar estado del bot
    """
    try:
        config = TelegramConfig.objects.filter(is_active=True).first()
        if config:
            return JsonResponse(
                {"status": "active", "bot_name": config.name, "configured": True}
            )
        else:
            return JsonResponse(
                {
                    "status": "inactive",
                    "configured": False,
                    "message": "No hay configuración activa",
                }
            )
    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)}, status=500)
