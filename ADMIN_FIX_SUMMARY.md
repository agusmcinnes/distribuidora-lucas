# Admin Navigation Fix - Multi-Tenant Support

## Problem Summary
The admin interface was breaking when switching between the superadmin panel (http://localhost:8000/admin/) and tenant panels (http://company.loc:8000/admin/) during video demonstrations.

### Errors Encountered:
1. **NoReverseMatch** errors for 'company' app_label
2. **Page not found (404)** errors when accessing certain admin sections
3. URL pattern conflicts when switching between schemas

## Root Cause
The middleware was attempting to dynamically register/unregister admin models based on the current schema, which caused:
- URL pattern conflicts
- Admin registry state corruption
- Inconsistent behavior when switching between schemas

## Solution Applied

### 1. Simplified TenantAdminMiddleware (`app/company/middleware.py`)
**Before:** Complex logic to register/unregister admins per request
**After:** Simple logic to only set admin titles dynamically

```python
def _set_admin_titles(self):
    """Only sets titles - no registration manipulation"""
    schema_name = connection.schema_name

    if schema_name == 'public':
        admin.site.site_header = "🏢 Distribuidora Lucas - Super Admin"
        # ...
    else:
        admin.site.site_header = f"🏢 {company_name} - Panel de Administración"
        # ...
```

### 2. Updated TelegramChat Admin (`app/telegram_bot/admin.py`)
**Strategy:** Use queryset filtering instead of module permission blocking

```python
def get_queryset(self, request):
    """Show all chats in public, filtered chats in tenant"""
    qs = super().get_queryset(request)

    if connection.schema_name == "public":
        return qs.all()  # Superadmin sees everything

    # Tenant sees only their company's chats
    current_company = Company.objects.get(schema_name=connection.schema_name)
    return qs.filter(company=current_company)
```

### 3. Static Admin Registration
**Change:** Removed conditional registration logic
**Result:** Admins are always registered, queryset filtering controls visibility

```python
# Always register - querysets handle filtering
admin.site.register(TelegramChat, TenantTelegramChatAdmin)
admin.site.register(TelegramMessage, TenantTelegramMessageAdmin)
```

## Benefits

1. **Stable URL Patterns:** URLs don't change when switching schemas
2. **No Registry Corruption:** Admin state remains consistent
3. **Clean Separation:** Logic in querysets instead of middleware
4. **Better Performance:** No registration overhead per request

## Testing Instructions

### Test 1: Superadmin Panel (Public Schema)
1. Open: `http://localhost:8000/admin/`
2. Verify you see:
   - 🏢 Distribuidora Lucas - Super Admin (header)
   - Company models (Company, Domain)
   - TelegramConfig (bot configuration)
   - All TelegramChats from all companies
   - User management for all companies

### Test 2: Tenant Panel
1. Open: `http://company.loc:8000/admin/` (replace with actual tenant domain)
2. Verify you see:
   - 🏢 [Company Name] - Panel de Administración (header)
   - NO Company/Domain models
   - NO TelegramConfig
   - Only TelegramChats for this company
   - Only users for this company

### Test 3: Switching Between Schemas
1. Open superadmin panel
2. Navigate around (click on models, etc.)
3. Switch to tenant panel in another tab
4. Navigate around tenant panel
5. Switch back to superadmin
6. **Expected:** No errors, both panels work correctly

### Test 4: Chat Management
**In Tenant Panel:**
1. Go to TelegramChats
2. Click "Agregar Chat de Telegram"
3. Verify:
   - Company selector shows only current company
   - Bot selector shows active bots
   - Setup instructions are visible

**In Superadmin Panel:**
1. Go to TelegramChats
2. Verify you see chats from ALL companies
3. Company column shows which company owns each chat

## Files Modified

1. `app/company/middleware.py` - Simplified to only set titles
2. `app/telegram_bot/admin.py` - Updated queryset filtering logic
3. `app/company/admin.py` - Removed conditional registration

## Rollback Instructions

If issues occur, restore previous versions from git:
```bash
git checkout HEAD~1 -- app/company/middleware.py
git checkout HEAD~1 -- app/telegram_bot/admin.py
docker-compose restart web
```

## Additional Notes

- The middleware now ONLY sets admin titles per request
- All visibility logic is handled by queryset filtering
- No dynamic admin registration/unregistration occurs
- This is the recommended Django pattern for multi-tenant admins
