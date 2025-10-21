"""
Comando para verificar si hay chats duplicados de Telegram
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from telegram_bot.models import TelegramChat


class Command(BaseCommand):
    help = 'Verifica si hay chats de Telegram duplicados'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('\n=== Verificando chats duplicados ===\n'))

        # Buscar chat_ids duplicados
        duplicates = (
            TelegramChat.objects.values('chat_id')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        if duplicates.exists():
            self.stdout.write(self.style.WARNING(f'⚠️  Encontrados {duplicates.count()} chat_ids duplicados:\n'))

            for dup in duplicates:
                chat_id = dup['chat_id']
                count = dup['count']

                chats = TelegramChat.objects.filter(chat_id=chat_id)

                self.stdout.write(self.style.ERROR(f'\n📱 Chat ID: {chat_id} ({count} registros)'))

                for chat in chats:
                    status = '✓ Activo' if chat.is_active else '✗ Inactivo'
                    email_alerts = '📧 Email alerts ON' if chat.email_alerts else '📧 Email alerts OFF'
                    self.stdout.write(
                        f'  - ID: {chat.id} | {chat.name} | {chat.company.name} | {status} | {email_alerts}'
                    )
        else:
            self.stdout.write(self.style.SUCCESS('✅ No hay chats duplicados\n'))

        # Mostrar todos los chats activos con email_alerts
        self.stdout.write(self.style.SUCCESS('\n=== Chats activos con alertas de email ===\n'))

        active_chats = TelegramChat.objects.filter(is_active=True, email_alerts=True).select_related('company', 'bot')

        if active_chats.exists():
            for chat in active_chats:
                self.stdout.write(
                    f'📱 {chat.name} (ID: {chat.chat_id}) | {chat.company.name} | Bot: {chat.bot.name if chat.bot else "N/A"}'
                )
        else:
            self.stdout.write(self.style.WARNING('No hay chats activos con alertas de email'))

        self.stdout.write(self.style.SUCCESS('\n=== Resumen ==='))
        self.stdout.write(f'Total chats: {TelegramChat.objects.count()}')
        self.stdout.write(f'Chats activos: {TelegramChat.objects.filter(is_active=True).count()}')
        self.stdout.write(f'Chats con email alerts: {TelegramChat.objects.filter(email_alerts=True).count()}')
        self.stdout.write(f'Chats activos con email alerts: {active_chats.count()}\n')
