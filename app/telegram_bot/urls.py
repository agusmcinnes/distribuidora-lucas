"""
URLs básicas para Telegram
"""

from django.urls import path
from .views import bot_status

app_name = "telegram_bot"

urlpatterns = [
    # Solo estado del bot
    path("status/", bot_status, name="bot_status"),
]
