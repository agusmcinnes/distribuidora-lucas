#!/usr/bin/env python
"""
Script para probar las alertas simplificadas de Telegram
"""

import os
import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
django.setup()

from emails.models import ReceivedEmail
from telegram_bot.services import TelegramNotificationService
from django.utils import timezone


def test_simplified_alert():
    """Prueba el sistema simplificado de alertas"""
    print("🤖 Probando sistema simplificado de alertas de Telegram...")

    # Importar después de configurar Django
    from company.models import Company

    # Obtener o crear una empresa
    company, _ = Company.objects.get_or_create(name="Empresa de Prueba")

    # Crear un email de prueba
    email = ReceivedEmail.objects.create(
        sender="test@example.com",
        subject="Prueba de alerta simplificada",
        body="Este es un email de prueba para verificar el sistema simplificado.",
        received_date=timezone.now(),
        company=company,
    )

    print(f"📧 Email de prueba creado: {email.subject}")

    # Enviar alerta directamente usando el servicio
    service = TelegramNotificationService()
    success = service.send_email_alert(email)

    if success:
        print("✅ Alerta enviada exitosamente!")
    else:
        print("❌ Error al enviar la alerta")

    # Limpiar
    email.delete()
    print("🧹 Email de prueba eliminado")


if __name__ == "__main__":
    test_simplified_alert()
