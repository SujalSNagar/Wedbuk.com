
from django.contrib import admin

from .models import VendorProfile


@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):

    list_display = [
        "business_name",
        "user",
        "city",
        "is_featured",
        "featured_order",
        "created_at",
    ]

    list_filter = [
        "city",
        "is_featured",
    ]

    search_fields = [
        "business_name",
        "user__email",
        "city__name",
    ]

    list_editable = [
        "is_featured",
        "featured_order",
    ]

    readonly_fields = [
        "created_at",
    ]

    filter_horizontal = [
        "categories",
    ]

    ordering = [
        "featured_order",
        "business_name",
    ]
