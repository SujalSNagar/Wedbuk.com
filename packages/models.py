from django.db import models

from vendors.models import VendorProfile
from categories.models import Category, Service


class Package(models.Model):

    vendor = models.ForeignKey(
        VendorProfile,
        related_name='packages',
        on_delete=models.CASCADE
    )

    title = models.CharField(max_length=200)

    description = models.TextField(
        help_text="Mention everything included in this package here."
    )

    min_guests = models.PositiveIntegerField(
    null=True,
    blank=True,
    verbose_name="Minimum Guests"
    )
    
    max_guests = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Maximum Guests"
    )
    
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    cover_image = models.ImageField(
        upload_to='packages/',
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class PackageCategory(models.Model):

    package = models.ForeignKey(
        Package,
        related_name='package_categories',
        on_delete=models.CASCADE
    )

    category = models.ForeignKey(
        Category,
        related_name='package_categories',
        on_delete=models.PROTECT
    )

    services = models.ManyToManyField(
        Service,
        blank=True,
        related_name='package_categories'
    )

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['package', 'category'],
                name='unique_package_category'
            )
        ]

    def __str__(self):
        return f"{self.package.title} - {self.category.name}"


class PackageImage(models.Model):

    package = models.ForeignKey(
        Package,
        related_name='gallery_images',
        on_delete=models.CASCADE
    )

    image = models.ImageField(
        upload_to='packages/gallery/'
    )

    caption = models.CharField(
        max_length=200,
        blank=True
    )

    order = models.PositiveIntegerField(
        default=0
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.package.title} - Image {self.order}"