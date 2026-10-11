
from django.contrib import admin
from .models import Package, PackageImage
 
 
class PackageImageInline(admin.TabularInline):
    model = PackageImage
    extra = 1
 
 
@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ['title', 'vendor', 'price', 'is_active']
    list_filter = ['is_active']
    search_fields = ['title', 'vendor__business_name']
    inlines = [PackageImageInline]
 