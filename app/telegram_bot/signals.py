"""
Señales de Django para el bot de Telegram
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# Las señales de email han sido removidas.
# PowerBI handler gestiona sus propias notificaciones.
