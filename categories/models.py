from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    icon = models.ImageField(
        upload_to='category_icons/',
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['display_order','name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Service(models.Model):
    category = models.ForeignKey(
        Category,
        related_name='services',
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']
        unique_together = ('category', 'name')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class CategoryAttribute(models.Model):

    FIELD_TYPE_CHOICES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('boolean', 'Yes / No'),
        ('dropdown', 'Dropdown'),
    ]

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='attributes'
    )

    label = models.CharField(
        max_length=150
    )

    field_type = models.CharField(
        max_length=20,
        choices=FIELD_TYPE_CHOICES,
        default='text'
    )

    options = models.TextField(
        blank=True,
        help_text='For dropdown: enter options separated by commas.'
    )

    unit = models.CharField(
        max_length=50,
        blank=True,
        help_text='Example: sq ft, guests, vehicles, hours'
    )

    help_text = models.CharField(
        max_length=255,
        blank=True,
        help_text='Small instruction shown to the vendor.'
    )

    is_required = models.BooleanField(
        default=False
    )

    order = models.PositiveIntegerField(
        default=0
    )

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.category.name} - {self.label}"

    class FieldType(models.TextChoices):
        TEXT = 'text', 'Text'
        NUMBER = 'number', 'Number'
        BOOLEAN = 'boolean', 'Yes/No'
        DROPDOWN = 'dropdown', 'Dropdown'

    category = models.ForeignKey(
        Category,
        related_name='attributes',
        on_delete=models.CASCADE
    )
    label = models.CharField(
        max_length=100,
        help_text="e.g. Seating Capacity"
    )
    field_type = models.CharField(
        max_length=20,
        choices=FieldType.choices,
        default=FieldType.TEXT
    )
    options = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "Only used for Dropdown type. "
            "Separate values with commas, "
            "e.g. Veg,Non-Veg,Both"
        )
    )
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(
        default=0,
        help_text="Controls the display order of this field"
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.category.name} - {self.label}"