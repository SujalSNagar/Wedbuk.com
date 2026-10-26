
from decimal import Decimal

from django.contrib import admin
from django.utils.html import format_html, format_html_join

from .models import BookingGroup, Booking
from payments.models import Payment


# ==================================================
# PAYMENT HELPERS
# ==================================================

def get_payment_totals(group):
    """
    Calculate payment figures from successful transactions.
    Payments belong to BookingGroup, not individual Booking.
    """
    successful_payments = [
        payment
        for payment in group.payments.all()
        if payment.status == Payment.Status.SUCCESS
    ]

    paid = sum(
        (payment.amount for payment in successful_payments),
        Decimal("0.00"),
    )

    advance_paid = sum(
        (
            payment.amount
            for payment in successful_payments
            if str(payment.payment_type).lower() == "advance"
        ),
        Decimal("0.00"),
    )

    total = group.total_amount or Decimal("0.00")
    balance = max(total - paid, Decimal("0.00"))

    percentage = Decimal(
        group.selected_payment_percentage or 0
    )

    required_advance = (
        total * percentage / Decimal("100")
    )

    if paid <= 0:
        status_label = "Unpaid"
        status_color = "#b91c1c"

    elif balance <= 0:
        status_label = "Fully Paid"
        status_color = "#15803d"

    elif advance_paid > 0 and paid <= required_advance:
        status_label = "Advance Paid"
        status_color = "#b45309"

    else:
        status_label = "Partial Payment"
        status_color = "#b45309"

    return {
        "total": total,
        "paid": paid,
        "advance_paid": advance_paid,
        "balance": balance,
        "required_advance": required_advance,
        "percentage": percentage,
        "status_label": status_label,
        "status_color": status_color,
        "successful_payments": successful_payments,
    }


def money(value):
    return f"₹ {value:,.2f}"


# ==================================================
# PAYMENT HISTORY INLINE
# ==================================================

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    can_delete = False
    show_change_link = True

    fields = (
        "created_at",
        "paid_at",
        "payment_type",
        "amount",
        "advance_percentage",
        "status",
        "razorpay_order_id",
        "transaction_id",
    )

    readonly_fields = fields

    ordering = ("-created_at",)

    def has_add_permission(self, request, obj=None):
        # Payments are created by the payment workflow.
        return False


# ==================================================
# BOOKING ITEMS INLINE
# ==================================================

class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    show_change_link = True

    fields = (
        "item_name_display",
        "vendor_display",
        "pricing_type_display",
        "rate_display",
        "calculation_display",
        "item_price_display",
        "status",
    )

    readonly_fields = (
        "item_name_display",
        "vendor_display",
        "pricing_type_display",
        "rate_display",
        "calculation_display",
        "item_price_display",
    )

    @admin.display(description="Item")
    def item_name_display(self, obj):
        return obj.item_name if obj.pk else "-"

    @admin.display(description="Vendor")
    def vendor_display(self, obj):
        if not obj.pk:
            return "-"

        if obj.listing_id:
            return obj.listing.vendor

        if obj.package_id:
            return obj.package.vendor

        return "Item unavailable"

    @admin.display(description="Pricing Type")
    def pricing_type_display(self, obj):
        if not obj.pk:
            return "-"

        if obj.listing_id:
            return obj.listing.get_pricing_type_display()

        return "Package price"

    @admin.display(description="Rate")
    def rate_display(self, obj):
        if not obj.pk:
            return "-"

        if obj.listing_id:
            return money(obj.listing.base_price)

        if obj.package_id:
            return money(obj.package.price)

        return "-"

    @admin.display(description="Calculation")
    def calculation_display(self, obj):
        if not obj.pk:
            return "-"

        if obj.listing_id:
            listing = obj.listing
            group = obj.group
            rate = listing.base_price

            if listing.pricing_type == listing.PricingType.PER_DAY:
                return f"{money(rate)} × {group.total_days} days"

            if listing.pricing_type == listing.PricingType.PER_PLATE:
                return (
                    f"{money(rate)} × "
                    f"{group.guest_count or 0} guests"
                )

            return "Fixed listing price"

        if obj.package_id:
            return "Package fixed price"

        return "Item unavailable"

    @admin.display(description="Item Total")
    def item_price_display(self, obj):
        return money(obj.item_price) if obj.pk else "-"


# ==================================================
# BOOKING GROUP ADMIN
# ==================================================

@admin.register(BookingGroup)
class BookingGroupAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "customer_display",
        "event_start_date",
        "event_end_date",
        "total_amount_display",
        "payment_status_display",
        "successful_payments_display",
        "remaining_amount_display",
        "created_at",
    )

    list_filter = (
        "event_start_date",
        "event_end_date",
        "created_at",
    )

    search_fields = (
        "full_name",
        "phone_number",
        "email",
        "customer__username",
        "customer__email",
    )

    date_hierarchy = "created_at"
    list_per_page = 20

    inlines = (BookingInline, PaymentInline)

    readonly_fields = (
        "total_days_display",
        "calculated_items_total_display",
        "required_advance_display",
        "payment_status_display",
        "successful_payments_display",
        "advance_paid_display",
        "remaining_amount_display",
        "created_at",
    )

    fieldsets = (
        (
            "Customer Information",
            {
                "fields": (
                    "customer",
                    "full_name",
                    "phone_number",
                    "email",
                )
            },
        ),
        (
            "Event Details",
            {
                "fields": (
                    "event_start_date",
                    "event_end_date",
                    "total_days_display",
                    "guest_count",
                    "notes",
                )
            },
        ),
        (
            "Booking Financial Summary",
            {
                "fields": (
                    "total_amount",
                    "calculated_items_total_display",
                    "selected_payment_percentage",
                    "required_advance_display",
                    "payment_status_display",
                    "advance_paid_display",
                    "amount_paid",
                    "successful_payments_display",
                    "remaining_amount",
                    "remaining_amount_display",
                )
            },
        ),
        (
            "Record Information",
            {
                "fields": ("created_at",)
            },
        ),
    )

    @admin.display(description="Customer")
    def customer_display(self, obj):
        return obj.full_name or str(obj.customer)

    @admin.display(description="Total Event Days")
    def total_days_display(self, obj):
        return obj.total_days

    @admin.display(description="Calculated Items Total")
    def calculated_items_total_display(self, obj):
        return money(obj.calculated_total_amount)

    @admin.display(description="Total Amount", ordering="total_amount")
    def total_amount_display(self, obj):
        return money(obj.total_amount)

    @admin.display(description="Payment Status")
    def payment_status_display(self, obj):
        data = get_payment_totals(obj)

        return format_html(
            '<strong style="color:{}">{}</strong>',
            data["status_color"],
            data["status_label"],
        )

    @admin.display(description="Required Advance")
    def required_advance_display(self, obj):
        data = get_payment_totals(obj)

        return (
            f'{money(data["required_advance"])} '
            f'({data["percentage"]}%)'
        )

    @admin.display(description="Advance Received")
    def advance_paid_display(self, obj):
        return money(get_payment_totals(obj)["advance_paid"])

    @admin.display(description="Total Paid", ordering="amount_paid")
    def successful_payments_display(self, obj):
        return format_html(
            '<strong style="color:#15803d">{}</strong>',
            money(get_payment_totals(obj)["paid"]),
        )

    @admin.display(description="Balance Remaining")
    def remaining_amount_display(self, obj):
        data = get_payment_totals(obj)

        return format_html(
            '<strong style="color:{}">{}</strong>',
            "#b45309" if data["balance"] > 0 else "#15803d",
            money(data["balance"]),
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("customer")
            .prefetch_related("payments", "bookings")
        )


# ==================================================
# INDIVIDUAL BOOKING ADMIN
# ==================================================

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "item_name_display",
        "vendor_display",
        "customer_display",
        "event_dates_display",
        "item_price_display",
        "group_payment_status_display",
        "group_paid_display",
        "group_balance_display",
        "status",
    )

    list_filter = (
        "status",
        "group__event_start_date",
        "created_at",
    )

    search_fields = (
        "listing__title",
        "package__title",
        "group__full_name",
        "group__phone_number",
        "group__email",
        "group__customer__username",
    )

    date_hierarchy = "created_at"
    list_per_page = 20

    readonly_fields = (
        "item_name_display",
        "vendor_display",
        "customer_display",
        "event_dates_display",
        "pricing_type_display",
        "rate_display",
        "calculation_display",
        "item_price_display",
        "group_payment_status_display",
        "group_required_advance_display",
        "group_advance_paid_display",
        "group_paid_display",
        "group_balance_display",
        "group_payment_history_display",
        "created_at",
    )

    fieldsets = (
        (
            "Booking Information",
            {
                "fields": (
                    "group",
                    "status",
                )
            },
        ),
        (
            "Item & Vendor",
            {
                "fields": (
                    "listing",
                    "package",
                    "item_name_display",
                    "vendor_display",
                )
            },
        ),
        (
            "Customer & Event",
            {
                "fields": (
                    "customer_display",
                    "event_dates_display",
                )
            },
        ),
        (
            "Price Breakdown",
            {
                "fields": (
                    "pricing_type_display",
                    "rate_display",
                    "calculation_display",
                    "item_price_display",
                )
            },
        ),
        (
            "Group Payment Summary",
            {
                "fields": (
                    "group_payment_status_display",
                    "group_required_advance_display",
                    "group_advance_paid_display",
                    "group_paid_display",
                    "group_balance_display",
                    "group_payment_history_display",
                )
            },
        ),
        (
            "Record Information",
            {
                "fields": ("created_at",)
            },
        ),
    )

    @admin.display(description="Item")
    def item_name_display(self, obj):
        return obj.item_name if obj.pk else "-"

    @admin.display(description="Vendor")
    def vendor_display(self, obj):
        if not obj.pk:
            return "-"

        if obj.listing_id:
            return obj.listing.vendor

        if obj.package_id:
            return obj.package.vendor

        return "Item unavailable"

    @admin.display(description="Customer")
    def customer_display(self, obj):
        if not obj.pk:
            return "-"

        return obj.group.full_name or str(obj.group.customer)

    @admin.display(description="Event Dates")
    def event_dates_display(self, obj):
        if not obj.pk:
            return "-"

        group = obj.group

        return (
            f"{group.event_start_date:%d %b %Y} – "
            f"{group.event_end_date:%d %b %Y} "
            f"({group.total_days} days)"
        )

    @admin.display(description="Pricing Type")
    def pricing_type_display(self, obj):
        if not obj.pk:
            return "-"

        if obj.listing_id:
            return obj.listing.get_pricing_type_display()

        return "Package price"

    @admin.display(description="Rate")
    def rate_display(self, obj):
        if not obj.pk:
            return "-"

        if obj.listing_id:
            return money(obj.listing.base_price)

        if obj.package_id:
            return money(obj.package.price)

        return "-"

    @admin.display(description="Calculation")
    def calculation_display(self, obj):
        if not obj.pk:
            return "-"

        if obj.listing_id:
            listing = obj.listing
            group = obj.group
            rate = listing.base_price

            if listing.pricing_type == listing.PricingType.PER_DAY:
                return f"{money(rate)} × {group.total_days} days"

            if listing.pricing_type == listing.PricingType.PER_PLATE:
                return (
                    f"{money(rate)} × "
                    f"{group.guest_count or 0} guests"
                )

            return "Fixed listing price"

        if obj.package_id:
            return "Package fixed price"

        return "Item unavailable"

    @admin.display(description="Calculated Item Total")
    def item_price_display(self, obj):
        return money(obj.item_price) if obj.pk else "-"

    def _payment_totals(self, obj):
        return get_payment_totals(obj.group)

    @admin.display(description="Group Payment Status")
    def group_payment_status_display(self, obj):
        data = self._payment_totals(obj)

        return format_html(
            '<strong style="color:{}">{}</strong>',
            data["status_color"],
            data["status_label"],
        )

    @admin.display(description="Required Advance")
    def group_required_advance_display(self, obj):
        data = self._payment_totals(obj)

        return (
            f'{money(data["required_advance"])} '
            f'({data["percentage"]}%)'
        )

    @admin.display(description="Advance Received")
    def group_advance_paid_display(self, obj):
        return money(self._payment_totals(obj)["advance_paid"])

    @admin.display(description="Group Total Paid")
    def group_paid_display(self, obj):
        return money(self._payment_totals(obj)["paid"])

    @admin.display(description="Group Balance Remaining")
    def group_balance_display(self, obj):
        data = self._payment_totals(obj)

        return format_html(
            '<strong style="color:{}">{}</strong>',
            "#b45309" if data["balance"] > 0 else "#15803d",
            money(data["balance"]),
        )

    @admin.display(description="Group Payment History")
    def group_payment_history_display(self, obj):
        payments = obj.group.payments.all().order_by("-created_at")

        if not payments.exists():
            return "No payment records"

        return format_html_join(
            "",
            (
                "<div style='padding:6px 0;"
                "border-bottom:1px solid #e7ded0'>"
                "<strong>{}</strong> — {} — {}"
                "<br><small>{}</small>"
                "</div>"
            ),
            (
                (
                    payment.get_payment_type_display(),
                    money(payment.amount),
                    payment.get_status_display(),
                    payment.paid_at or payment.created_at,
                )
                for payment in payments
            ),
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "group",
                "group__customer",
                "listing",
                "package",
            )
            .prefetch_related("group__payments")
        )
