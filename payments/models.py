from django.db import models
from bookings.models import BookingGroup


class Payment(models.Model):
    class PaymentType(models.TextChoices):
        ADVANCE = "advance", "Advance Payment"
        FULL = "full", "Full Payment"
        BALANCE = "balance", "Balance Payment"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    booking_group = models.ForeignKey(BookingGroup, related_name="payments", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, default=PaymentType.FULL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    advance_percentage = models.PositiveSmallIntegerField(null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, db_index=True)
    transaction_id = models.CharField(max_length=100, blank=True, db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.booking_group} - ₹{self.amount} ({self.status})"
