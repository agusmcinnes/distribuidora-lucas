#!/usr/bin/env python
"""
Script para probar que las señales automáticas funcionen
"""

import os
import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
django.setup()

from emails.models import ReceivedEmail
from company.models import Company
from django.utils import timezone


def test_automatic_signals():
    """Prueba que las señales automáticas funcionen"""
    print("🔄 Probando señales automáticas de alertas...")

    # Obtener o crear una empresa
    company, _ = Company.objects.get_or_create(name="Empresa de Prueba")

    # Crear un email - esto debería disparar automáticamente la señal
    print("📧 Creando email (debería disparar alerta automática)...")
    email = ReceivedEmail.objects.create(
        sender="urgent@example.com",
        subject="URGENTE: Problema crítico detectado",
        body="Este es un email URGENTE que debería generar una alerta de alta prioridad.",
        received_date=timezone.now(),
        company=company,
    )

    print(f"✅ Email creado: {email.subject}")
    print("🤖 Si las señales funcionan, deberías ver una alerta en Telegram")

    # Esperar un momento
    import time

    print("⏳ Esperando 3 segundos...")
    time.sleep(3)

    # Limpiar
    email.delete()
    print("🧹 Email de prueba eliminado")
    print("✨ Prueba completada!")


if __name__ == "__main__":
    test_automatic_signals()
