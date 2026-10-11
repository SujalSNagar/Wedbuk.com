from django.contrib import admin

from .models import BookingGroup, Booking


class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0


@admin.register(BookingGroup)
class BookingGroupAdmin(admin.ModelAdmin):
    list_display = [
        'customer',
        'event_start_date',
        'event_end_date',
        'total_amount',
    ]
    list_filter = [
        'event_start_date',
        'event_end_date',
    ]
    inlines = [BookingInline]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['item_name', 'vendor', 'group', 'status']
    list_filter = ['status']