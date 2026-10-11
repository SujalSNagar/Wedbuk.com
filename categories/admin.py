from django.contrib import admin

from .models import Category, Service, CategoryAttribute


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1
    prepopulated_fields = {
        'slug': ('name',)
    }


class CategoryAttributeInline(admin.TabularInline):
    model = CategoryAttribute
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name','display_order','is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {
        'slug': ('name',)
    }
    inlines = [
        ServiceInline,
        CategoryAttributeInline,
    ]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'category',
        'display_order',
        'is_active',
    ]
    list_filter = [
        'category',
        'is_active',
    ]
    search_fields = [
        'name',
        'category__name',
    ]
    prepopulated_fields = {
        'slug': ('name',)
    }


@admin.register(CategoryAttribute)
class CategoryAttributeAdmin(admin.ModelAdmin):
    list_display = [
        'label',
        'category',
        'field_type',
        'is_required',
        'order',
    ]
    list_filter = [
        'category',
        'field_type',
        'is_required',
    ]
    search_fields = [
        'label',
        'category__name',
    ]