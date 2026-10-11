from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from categories.models import Category, Service
from core.models import EventType
from vendors.models import VendorProfile
from locations.models import State, City


# =========================================================
# VIDEO FILE SIZE VALIDATION
# =========================================================

def validate_video_size(file):
    max_size = 10 * 1024 * 1024  # 10 MB

    if file.size > max_size:
        raise ValidationError(
            'Video file size cannot be more than 10 MB.'
        )


# =========================================================
# LISTING
# =========================================================

class Listing(models.Model):

    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='listings'
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='listings'
    )

    title = models.CharField(
        max_length=200
    )

    description = models.TextField()

    base_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    min_guests = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Minimum Guests'
    )

    max_guests = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Maximum Guests'
    )

    address_line_1 = models.CharField(
        max_length=255
    )

    address_line_2 = models.CharField(
        max_length=255,
        blank=True
    )

    state = models.ForeignKey(
        State,
        on_delete=models.PROTECT,
        related_name='listings'
    )

    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='listings'
    )

    pincode = models.CharField(
        max_length=10
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True
    )

    cover_image = models.ImageField(
        upload_to='listings/',
        blank=True,
        null=True
    )

    event_types = models.ManyToManyField(
        EventType,
        blank=True,
        related_name='listings'
    )

    services = models.ManyToManyField(
        Service,
        blank=True,
        related_name='listings'
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def clean(self):

        if (
            self.state_id
            and self.city_id
            and self.city.state_id != self.state_id
        ):
            raise ValidationError({
                'city':
                    'Selected city does not belong to the selected state.'
            })

        if (
            self.min_guests is not None
            and self.max_guests is not None
            and self.min_guests > self.max_guests
        ):
            raise ValidationError({
                'max_guests':
                    'Maximum guests cannot be less than minimum guests.'
            })


# =========================================================
# LISTING ATTRIBUTE VALUE
# =========================================================

class ListingAttributeValue(models.Model):

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='attribute_values'
    )

    attribute = models.ForeignKey(
        'categories.CategoryAttribute',
        on_delete=models.CASCADE,
        related_name='listing_values'
    )

    value = models.TextField(
        blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'listing',
                    'attribute'
                ],
                name='unique_listing_attribute'
            )
        ]

    def __str__(self):
        return f"{self.listing.title} - {self.attribute.label}"


# =========================================================
# LISTING GALLERY IMAGES
# =========================================================

class ListingImage(models.Model):

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='images'
    )

    image = models.ImageField(
        upload_to='listings/gallery/'
    )

    display_order = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            'display_order',
            'id'
        ]

    def __str__(self):
        return f"{self.listing.title} - Image {self.id}"


# =========================================================
# LISTING VIDEOS
# =========================================================

class ListingVideo(models.Model):

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='videos'
    )

    video = models.FileField(
        upload_to='listings/videos/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    'mp4',
                    'webm',
                    'mov',
                    'avi'
                ]
            ),
            validate_video_size,
        ]
    )

    display_order = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            'display_order',
            'id'
        ]

    def __str__(self):
        return f"{self.listing.title} - Video {self.id}"


# =========================================================
# LISTING AVAILABILITY
# =========================================================

class ListingAvailability(models.Model):

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='availability_periods'
    )

    available_from = models.DateField()

    available_until = models.DateField()

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            'available_from'
        ]

    def clean(self):

        if (
            self.available_from
            and self.available_until
            and self.available_from > self.available_until
        ):
            raise ValidationError({
                'available_until':
                    'Available until date cannot be before available from date.'
            })

    def __str__(self):
        return (
            f"{self.listing.title} | "
            f"{self.available_from} → "
            f"{self.available_until}"
        )


# =========================================================
# LISTING BLOCKED DATE
# =========================================================

class ListingBlockedDate(models.Model):

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='blocked_dates'
    )

    date = models.DateField()

    reason = models.CharField(
        max_length=255,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            'date'
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'listing',
                    'date'
                ],
                name='unique_blocked_date_per_listing'
            )
        ]

    def __str__(self):
        return f"{self.listing.title} | {self.date}"