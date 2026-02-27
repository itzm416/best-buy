from django.contrib import admin
from authenticationapp.models import User
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

@admin.register(User)
class User_ModelAdmin(UserAdmin):
    list_display = ['email','mfa_enabled']
    ordering = ['email']

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    fieldsets = (
        (None, {'fields': (
            'email',
            'password',
        )}),
        (_('Django permissions'), {'fields': (
            'is_active',
            'is_staff',
            'is_superuser',
            'user_permissions',
            'groups',
        )}),
    )