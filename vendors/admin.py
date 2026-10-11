from django.contrib import admin

from .models import VendorProfile


@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):

    list_display = [
        'business_name',
        'user',
        'city',
        'created_at',
    ]

    list_filter = [
        'city',
    ]

    search_fields = [
        'business_name',
        'user__email',
        'city',
    ]

    readonly_fields = [
        'created_at',
    ]

    filter_horizontal = [
        'categories',
    ]