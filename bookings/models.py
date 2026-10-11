from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings

from listings.models import Listing
from packages.models import Package


class BookingGroup(models.Model):

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='booking_groups',
        on_delete=models.CASCADE
    )

    # Customer details at the time of booking
    full_name = models.CharField(
        max_length=150,
        blank=True
    )

    phone_number = models.CharField(
        max_length=15,
        blank=True
    )

    email = models.EmailField(
        blank=True
    )

    event_start_date = models.DateField()

    event_end_date = models.DateField()

    guest_count = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']

    def clean(self):

        if (
            self.event_start_date
            and self.event_end_date
            and self.event_start_date > self.event_end_date
        ):
            raise ValidationError({
                'event_end_date':
                    'End date cannot be before start date.'
            })

    @property
    def total_days(self):

        if not self.event_start_date or not self.event_end_date:
            return 0

        return (
            self.event_end_date - self.event_start_date
        ).days + 1

    @property
    def total_amount(self):

        return sum(
            booking.item_price
            for booking in self.bookings.all()
        )

    def __str__(self):

        return (
            f"{self.full_name or self.customer} - "
            f"{self.event_start_date} → "
            f"{self.event_end_date}"
        )


class Booking(models.Model):

    class Status(models.TextChoices):

        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'
        COMPLETED = 'completed', 'Completed'

    group = models.ForeignKey(
        BookingGroup,
        related_name='bookings',
        on_delete=models.CASCADE
    )

    listing = models.ForeignKey(
        Listing,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='bookings'
    )

    package = models.ForeignKey(
        Package,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='bookings'
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']

    def clean(self):

        if not self.listing and not self.package:
            raise ValidationError(
                "Select either a listing or a package for this booking."
            )

        if self.listing and self.package:
            raise ValidationError(
                "A booking can only have a listing or a package, not both."
            )

    @property
    def vendor(self):

        return (
            self.listing.vendor
            if self.listing
            else self.package.vendor
        )

    @property
    def item_name(self):

        return (
            self.listing.title
            if self.listing
            else self.package.title
        )

    @property
    def item_price(self):

        return (
            self.listing.base_price
            if self.listing
            else self.package.price
        )

    def __str__(self):

        return (
            f"{self.item_name} "
            f"({self.group.full_name or self.group.customer})"
        )