"""
Comando para limpiar chats duplicados de Telegram
Mantiene solo el chat más reciente y elimina los duplicados
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from telegram_bot.models import TelegramChat


class Command(BaseCommand):
    help = 'Limpia chats de Telegram duplicados, manteniendo solo el más reciente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se eliminaría sin hacer cambios',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ejecuta la limpieza sin confirmación',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        self.stdout.write(self.style.SUCCESS('\n=== Limpieza de chats duplicados ===\n'))

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  Modo DRY RUN - No se harán cambios\n'))

        # Buscar chat_ids duplicados
        duplicates = (
            TelegramChat.objects.values('chat_id')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        if not duplicates.exists():
            self.stdout.write(self.style.SUCCESS('✅ No hay chats duplicados para limpiar\n'))
            return

        self.stdout.write(self.style.WARNING(f'⚠️  Encontrados {duplicates.count()} chat_ids duplicados\n'))

        total_to_delete = 0
        deleted_count = 0

        for dup in duplicates:
            chat_id = dup['chat_id']
            count = dup['count']

            # Obtener todos los chats con este chat_id, ordenados por fecha de creación (más reciente primero)
            chats = TelegramChat.objects.filter(chat_id=chat_id).order_by('-created_at')

            self.stdout.write(f'\n📱 Chat ID: {chat_id} ({count} registros)')

            # Mantener el más reciente (primero en la lista)
            chat_to_keep = chats.first()
            self.stdout.write(self.style.SUCCESS(f'  ✅ Mantener: ID={chat_to_keep.id} | {chat_to_keep.name} | {chat_to_keep.company.name} | Creado: {chat_to_keep.created_at}'))

            # Eliminar los demás
            chats_to_delete = chats[1:]  # Todos excepto el primero
            total_to_delete += chats_to_delete.count()

            for chat in chats_to_delete:
                self.stdout.write(self.style.ERROR(f'  ❌ Eliminar: ID={chat.id} | {chat.name} | {chat.company.name} | Creado: {chat.created_at}'))

                if not dry_run:
                    # Verificar si hay códigos de registro asociados
                    if hasattr(chat, 'registration_code_used') and chat.registration_code_used.exists():
                        for code in chat.registration_code_used.all():
                            # Re-asignar el código al chat que se mantiene
                            code.used_by_chat = chat_to_keep
                            code.save()
                            self.stdout.write(f'     → Código {code.code} reasignado al chat que se mantiene')

                    # Eliminar el chat duplicado
                    chat.delete()
                    deleted_count += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n💡 Se eliminarían {total_to_delete} chats duplicados (ejecuta sin --dry-run para aplicar)\n'))
        else:
            if not force:
                confirm = input(f'\n⚠️  ¿Estás seguro de que quieres eliminar {total_to_delete} chats? (sí/no): ')
                if confirm.lower() not in ['sí', 'si', 'yes', 'y']:
                    self.stdout.write(self.style.ERROR('❌ Operación cancelada\n'))
                    return

            self.stdout.write(self.style.SUCCESS(f'\n✅ Eliminados {deleted_count} chats duplicados\n'))

        # Mostrar resumen final
        self.stdout.write(self.style.SUCCESS('=== Resumen final ==='))
        remaining_chats = TelegramChat.objects.count()
        active_chats = TelegramChat.objects.filter(is_active=True, email_alerts=True).count()
        self.stdout.write(f'Total chats restantes: {remaining_chats}')
        self.stdout.write(f'Chats activos con email alerts: {active_chats}\n')
