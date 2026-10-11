from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


class UserAdmin(BaseUserAdmin):
    model = User

    ordering = ['email']

    list_display = [
        'email',
        'full_name',
        'phone_number',
        'role',
        'is_staff',
        'is_active',
    ]

    fieldsets = (
        (None, {
            'fields': (
                'email',
                'password',
            )
        }),

        ('Personal Info', {
            'fields': (
                'full_name',
                'phone_number',
                'role',
            )
        }),

        ('Permissions', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
            )
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'full_name',
                'phone_number',
                'password1',
                'password2',
                'role',
            ),
        }),
    )

    search_fields = (
        'email',
        'full_name',
        'phone_number',
    )


admin.site.register(User, UserAdmin)