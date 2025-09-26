from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.http import JsonResponse
from django_tenants.utils import tenant_context
from .models import Company
from .decorators import public_schema_required, superuser_and_public_schema_required


@staff_member_required
@public_schema_required
def cross_tenant_dashboard(request):
    """Dashboard con datos de todos los tenants"""
    data = []
    
    for company in Company.objects.filter(is_active=True).exclude(schema_name='public'):
        tenant_data = {
            'company': company,
            'users': 0,
            'emails': 0,
            'telegram_bots': 0,
            'recent_emails': []
        }
        
        try:
            with tenant_context(company):
                # Contar usuarios
                from django.contrib.auth.models import User
                tenant_data['users'] = User.objects.count()
                
                # Contar emails
                from emails.models import ReceivedEmail
                tenant_data['emails'] = ReceivedEmail.objects.count()
                
                # Obtener emails recientes
                recent_emails = ReceivedEmail.objects.order_by('-created_at')[:5]
                tenant_data['recent_emails'] = [
                    {
                        'subject': email.subject,
                        'sender': email.sender,
                        'created_at': email.created_at,
                        'priority': email.priority
                    }
                    for email in recent_emails
                ]
                
                # Contar bots de Telegram
                from telegram_bot.models import TelegramConfig
                tenant_data['telegram_bots'] = TelegramConfig.objects.count()
                
                # Obtener bots recientes
                tenant_data['telegram_bot_names'] = [
                    bot.name for bot in TelegramConfig.objects.all()[:3]
                ]
                
        except Exception as e:
            tenant_data['error'] = str(e)
            
        data.append(tenant_data)
    
    return render(request, 'admin/cross_tenant_dashboard.html', {
        'title': 'Dashboard Multi-Tenant',
        'tenants_data': data
    })


@staff_member_required
@public_schema_required
def cross_tenant_emails_api(request):
    """API para obtener emails de todos los tenants"""
    emails = []
    
    for company in Company.objects.filter(is_active=True).exclude(schema_name='public'):
        try:
            with tenant_context(company):
                from emails.models import ReceivedEmail
                tenant_emails = ReceivedEmail.objects.all()[:50]  # Limitamos para performance
                
                for email in tenant_emails:
                    emails.append({
                        'company': company.name,
                        'subject': email.subject,
                        'sender': email.sender,
                        'body': email.body[:200] + '...' if len(email.body) > 200 else email.body,
                        'created_at': email.created_at.isoformat(),
                        'priority': email.priority,
                        'status': email.status,
                    })
        except:
            continue
    
    return JsonResponse({'emails': emails})


@staff_member_required
@public_schema_required
def cross_tenant_users_api(request):
    """API para obtener usuarios de todos los tenants"""
    users = []
    
    for company in Company.objects.filter(is_active=True).exclude(schema_name='public'):
        try:
            with tenant_context(company):
                from django.contrib.auth.models import User
                tenant_users = User.objects.all()
                
                for user in tenant_users:
                    users.append({
                        'company': company.name,
                        'username': user.username,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'is_active': user.is_active,
                        'is_staff': user.is_staff,
                        'date_joined': user.date_joined.isoformat(),
                    })
        except:
            continue
    
    return JsonResponse({'users': users})


@staff_member_required
@public_schema_required
def custom_admin_index(request):
    """Custom admin index with cross-tenant statistics"""
    from django.contrib.admin import site
    from django_tenants.utils import tenant_context
    from django.db import connection
    
    # Solo mostrar estadísticas si estamos en el esquema público
    if connection.schema_name != 'public':
        # Si estamos en un tenant, redirigir al admin normal
        from django.contrib.admin.views.decorators import staff_member_required
        from django.shortcuts import redirect
        return redirect('/admin/')
    
    # Get basic admin context
    context = {
        'title': 'Administración del sitio',
        'site_title': site.site_title,
        'site_header': site.site_header,
        'site_url': site.site_url,
        'has_permission': request.user.is_active and request.user.is_staff,
        'available_apps': site.get_app_list(request),
    }
    
    # Add cross-tenant statistics
    companies = Company.objects.filter(is_active=True).exclude(schema_name='public')
    total_users = 0
    total_emails = 0
    total_bots = 0
    
    for company in companies:
        try:
            with tenant_context(company):
                from django.contrib.auth.models import User as DjangoUser
                total_users += DjangoUser.objects.count()
                
                from emails.models import ReceivedEmail
                total_emails += ReceivedEmail.objects.count()
                
                from telegram_bot.models import TelegramConfig
                total_bots += TelegramConfig.objects.count()
        except Exception as e:
            # Log error but continue
            continue
    
    context.update({
        'companies_count': companies.count(),
        'total_users': total_users,
        'total_emails': total_emails,
        'total_bots': total_bots,
    })
    
    return render(request, 'admin/index.html', context)
