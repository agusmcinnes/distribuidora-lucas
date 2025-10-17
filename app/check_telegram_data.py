#!/usr/bin/env python
"""Script temporal para verificar datos de telegram_bot"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from telegram_bot.models import TelegramConfig, TelegramChat, TelegramMessage

print("=" * 60)
print("DATOS ACTUALES EN TELEGRAM_BOT")
print("=" * 60)

print("\n=== TelegramConfig (Configuración del Bot) ===")
configs = TelegramConfig.objects.all()
print(f"Total: {configs.count()} configuraciones")
if configs.exists():
    for config in configs:
        print(f"  - {config.name} ({'Activo' if config.is_active else 'Inactivo'})")
        print(f"    Token: {config.bot_token[:20]}..." if config.bot_token else "    Sin token")
else:
    print("  (No hay configuraciones)")

print("\n=== TelegramChat (Chats configurados) ===")
chats = TelegramChat.objects.all()
print(f"Total: {chats.count()} chats")
if chats.exists():
    for chat in chats:
        print(f"  - {chat.name} (ID: {chat.chat_id})")
        print(f"    Tipo: {chat.chat_type}, Alertas email: {chat.email_alerts}")
else:
    print("  (No hay chats configurados)")

print("\n=== TelegramMessage (Mensajes enviados) ===")
messages = TelegramMessage.objects.all()
print(f"Total: {messages.count()} mensajes")
if messages.exists():
    print("  Últimos 5 mensajes:")
    for msg in messages.order_by('-created_at')[:5]:
        print(f"  - {msg.subject[:40]}... ({msg.status})")
        print(f"    Fecha: {msg.created_at}")
else:
    print("  (No hay mensajes)")

print("\n" + "=" * 60)
print("RESUMEN:")
print("=" * 60)
print(f"Si eliminas estos datos:")
print(f"  - Se borrarán {configs.count()} configuraciones de bot")
print(f"  - Se borrarán {chats.count()} chats configurados")
print(f"  - Se borrarán {messages.count()} mensajes de historial")
print("\n⚠️  IMPORTANTE:")
print("  - Las configuraciones y chats se pueden volver a crear")
print("  - Los mensajes son solo historial, no afectan funcionalidad")
print("  - Después de borrar, podrás configurar todo de nuevo")
print("=" * 60)
