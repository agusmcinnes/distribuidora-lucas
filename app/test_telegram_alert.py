#!/usr/bin/env python3
"""
Script para probar el envío de alertas de Telegram sin Celery
"""

import os
import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
django.setup()

from telegram_bot.services import TelegramNotificationService

print("🚀 Enviando alerta de prueba directamente...")

try:
    service = TelegramNotificationService()
    results = service.send_email_alert(
        email_subject="🧪 PRUEBA - Nuevo pedido urgente",
        email_sender="cliente@empresa.com",
        email_priority="high",
        email_body_preview="Este es un pedido muy importante que necesita atención inmediata. Por favor revisar lo antes posible.",
    )

    print(f"\n📊 Resultados:")
    for result in results:
        if result.get("success"):
            print(f'✅ Mensaje enviado a: {result["chat"]}')
        else:
            error = result.get("error", "Error desconocido")
            print(f'❌ Error enviando a {result["chat"]}: {error}')

except Exception as e:
    print(f"❌ Error: {str(e)}")

print("\n🏁 Prueba completada")
