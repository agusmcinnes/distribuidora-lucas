#!/usr/bin/env python3
"""
Script para obtener Chat ID de Telegram
"""

import os
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv("../.env")
token = os.getenv("TELEGRAM_BOT_TOKEN")

if not token:
    print("❌ No se encontró TELEGRAM_BOT_TOKEN en el .env")
    exit(1)

print(f"🤖 Usando bot token: {token[:10]}...")
print("📡 Obteniendo updates...")

try:
    response = requests.get(f"https://api.telegram.org/bot{token}/getUpdates")
    data = response.json()

    if data.get("ok"):
        updates = data.get("result", [])
        if updates:
            print(f"✅ Encontrados {len(updates)} mensajes")
            print("")
            for update in updates[-3:]:  # Últimos 3 mensajes
                if "message" in update:
                    chat = update["message"]["chat"]
                    print(f'💬 Chat ID: {chat["id"]}')
                    print(
                        f'👤 Nombre: {chat.get("first_name", "")} {chat.get("last_name", "")}'
                    )
                    print(f'📝 Username: @{chat.get("username", "sin username")}')
                    print(f'🔤 Tipo: {chat.get("type", "unknown")}')
                    print(f'📩 Mensaje: {update["message"].get("text", "[sin texto]")}')
                    print("-" * 50)
        else:
            print("⚠️ No se encontraron mensajes.")
            print(
                "📱 ENVÍA UN MENSAJE A TU BOT PRIMERO y vuelve a ejecutar este script."
            )
    else:
        print(f'❌ Error: {data.get("description", "Error desconocido")}')

except Exception as e:
    print(f"❌ Error de conexión: {str(e)}")
    print("🔧 Verifica que tu token sea correcto y tengas internet.")
