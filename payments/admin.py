
from django.contrib import admin
from .models import Payment
 
 
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['booking_group', 'amount', 'payment_type', 'status', 'created_at']
    list_filter = ['status', 'payment_type']
    search_fields = ['transaction_id']