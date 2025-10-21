"""
Comando para limpiar chats de Telegram huérfanos (sin usuario asociado)
"""

from django.core.management.base import BaseCommand
from django.db import connection
from telegram_bot.models import TelegramChat
from company.models import Company


class Command(BaseCommand):
    help = 'Limpia chats de Telegram que no tienen usuario asociado'

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

        self.stdout.write(self.style.SUCCESS('\n=== Limpieza de chats huérfanos ===\n'))

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  Modo DRY RUN - No se harán cambios\n'))

        # Cambiar al esquema público
        original_schema = connection.schema_name
        connection.set_schema('public')

        try:
            # Obtener todos los chats
            all_chats = TelegramChat.objects.select_related('company').all()

            orphan_chats = []

            for chat in all_chats:
                company = chat.company

                # Cambiar al schema de la empresa
                connection.set_schema(company.schema_name)

                from user.models import User

                # Buscar si hay algún usuario con este chat_id
                user_exists = User.objects.filter(telegram_chat_id=str(chat.chat_id)).exists()

                if not user_exists:
                    orphan_chats.append(chat)
                    self.stdout.write(
                        self.style.WARNING(
                            f'🗑️  Chat huérfano: {chat.name} (ID: {chat.chat_id}) | {company.name} | Sin usuario asociado'
                        )
                    )

            # Volver al schema público
            connection.set_schema('public')

            if not orphan_chats:
                self.stdout.write(self.style.SUCCESS('✅ No hay chats huérfanos\n'))
                return

            total_orphans = len(orphan_chats)
            self.stdout.write(self.style.WARNING(f'\n⚠️  Encontrados {total_orphans} chats huérfanos\n'))

            if dry_run:
                self.stdout.write(self.style.WARNING(f'💡 Se eliminarían {total_orphans} chats (ejecuta sin --dry-run para aplicar)\n'))
                return

            if not force:
                confirm = input(f'\n⚠️  ¿Estás seguro de que quieres eliminar {total_orphans} chats huérfanos? (sí/no): ')
                if confirm.lower() not in ['sí', 'si', 'yes', 'y']:
                    self.stdout.write(self.style.ERROR('❌ Operación cancelada\n'))
                    return

            # Eliminar chats huérfanos
            deleted_count = 0
            for chat in orphan_chats:
                chat.delete()
                deleted_count += 1
                self.stdout.write(self.style.SUCCESS(f'✅ Eliminado: {chat.name} ({chat.chat_id})'))

            self.stdout.write(self.style.SUCCESS(f'\n✅ Eliminados {deleted_count} chats huérfanos\n'))

            # Mostrar resumen
            remaining_chats = TelegramChat.objects.count()
            active_chats = TelegramChat.objects.filter(is_active=True, email_alerts=True).count()

            self.stdout.write(self.style.SUCCESS('=== Resumen final ==='))
            self.stdout.write(f'Total chats restantes: {remaining_chats}')
            self.stdout.write(f'Chats activos con email alerts: {active_chats}\n')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}\n'))
        finally:
            # Asegurar que volvemos al schema original
            connection.set_schema(original_schema)
