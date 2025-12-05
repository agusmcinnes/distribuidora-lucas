"""
Management command para crear una empresa completa con tenant y usuario administrador
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django_tenants.utils import tenant_context
from company.models import Company, Domain
from user.models import Role, User


class Command(BaseCommand):
    help = 'Crea una empresa completa con tenant, dominio y usuario administrador'

    def add_arguments(self, parser):
        parser.add_argument(
            'company_name',
            type=str,
            help='Nombre de la empresa'
        )
        parser.add_argument(
            'schema_name',
            type=str,
            help='Nombre del schema (sin espacios, solo letras, números y guiones bajos)'
        )
        parser.add_argument(
            'domain',
            type=str,
            help='Dominio para acceder (ej: empresa.localhost)'
        )
        parser.add_argument(
            'admin_username',
            type=str,
            help='Usuario administrador'
        )
        parser.add_argument(
            'admin_email',
            type=str,
            help='Email del administrador'
        )
        parser.add_argument(
            '--admin-password',
            type=str,
            help='Contraseña del administrador (si no se proporciona, se pedirá interactivamente)'
        )
        parser.add_argument(
            '--inactive',
            action='store_true',
            help='Crear la empresa como inactiva'
        )

    def handle(self, *args, **options):
        company_name = options['company_name']
        schema_name = options['schema_name']
        domain = options['domain']
        admin_username = options['admin_username']
        admin_email = options['admin_email']
        admin_password = options['admin_password']
        is_active = not options['inactive']

        # Validaciones básicas
        if Company.objects.filter(schema_name=schema_name).exists():
            raise CommandError(f'Ya existe una empresa con el schema "{schema_name}"')
        
        if Domain.objects.filter(domain=domain).exists():
            raise CommandError(f'Ya existe el dominio "{domain}"')

        # Pedir contraseña si no se proporcionó
        if not admin_password:
            import getpass
            admin_password = getpass.getpass('Contraseña del administrador: ')
            confirm_password = getpass.getpass('Confirmar contraseña: ')
            
            if admin_password != confirm_password:
                raise CommandError('Las contraseñas no coinciden')

        if len(admin_password) < 8:
            raise CommandError('La contraseña debe tener al menos 8 caracteres')

        try:
            with transaction.atomic():
                self.stdout.write(f'Creando empresa "{company_name}"...')
                
                # Crear la empresa (esto crea automáticamente el esquema)
                company = Company.objects.create(
                    name=company_name,
                    schema_name=schema_name,
                    is_active=is_active
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Empresa creada con schema: {schema_name}')
                )
                
                # Crear el dominio
                domain_obj = Domain.objects.create(
                    domain=domain,
                    tenant=company,
                    is_primary=True
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Dominio creado: {domain}')
                )
                
                # Crear el usuario administrador en el tenant
                self._create_admin_user(company, admin_username, admin_email, admin_password)
                
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('🎉 ¡Empresa creada exitosamente!'))
                self.stdout.write('')
                self.stdout.write('📋 Información de acceso:')
                self.stdout.write(f'   🌐 URL: http://{domain}/admin/')
                self.stdout.write(f'   👤 Usuario: {admin_username}')
                self.stdout.write(f'   📧 Email: {admin_email}')
                self.stdout.write(f'   🔑 Contraseña: (la que configuraste)')
                self.stdout.write('')
                
                if not is_active:
                    self.stdout.write(
                        self.style.WARNING('⚠️  La empresa fue creada como INACTIVA')
                    )
                
        except Exception as e:
            raise CommandError(f'Error al crear la empresa: {str(e)}')

    def _create_admin_user(self, company, username, email, password):
        """Crea el usuario administrador en el esquema del tenant"""
        self.stdout.write('Configurando usuario administrador...')
        
        with tenant_context(company):
            # Crear usuario de Django Auth
            admin_user = DjangoUser.objects.create(
                username=username,
                email=email,
                password=make_password(password),
                is_staff=True,
                is_superuser=True,
                is_active=True,
                first_name="Administrador",
                last_name=company.name
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Usuario Django Auth creado: {username}')
            )
            
            # Crear roles básicos
            manager_role, created = Role.objects.get_or_create(
                type='manager',
                defaults={'description': 'Rol de administrador con acceso completo'}
            )
            if created:
                self.stdout.write('✅ Rol Manager creado')
            
            supervisor_role, created = Role.objects.get_or_create(
                type='supervisor', 
                defaults={'description': 'Rol de supervisor con acceso limitado'}
            )
            if created:
                self.stdout.write('✅ Rol Supervisor creado')
            
            client_role, created = Role.objects.get_or_create(
                type='client',
                defaults={'description': 'Rol de cliente básico'}
            )
            if created:
                self.stdout.write('✅ Rol Client creado')
            
            # Crear usuario del sistema personalizado
            custom_user = User.objects.create(
                name=f"Administrador {company.name}",
                email=email,
                role=manager_role,
                company=company,
                is_active=True,
                can_receive_alerts=True
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Usuario del sistema creado: {custom_user.name}')
            )