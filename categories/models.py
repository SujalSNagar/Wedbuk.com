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
        ('dropdown', 'Dropdown (single choice)'),
        ('multiselect', 'Multiple Select (vendor can pick many)'),
    ]

    # Special attributes feed fixed Listing columns that the search /
    # budget planner filters use (e.g. guest capacity).
    SPECIAL_KEY_CHOICES = [
        ('', 'None (normal field)'),
        ('min_guests', 'Minimum Guests'),
        ('max_guests', 'Maximum Guests'),
    ]

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='attributes'
    )

    # The attribute is shown ONLY when vendor picks this service.
    # (null kept only so old category-wide rows do not break)
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='attributes',
        null=True,
        blank=True
    )

    label = models.CharField(
        max_length=150,
        help_text='e.g. Seating Capacity'
    )

    field_type = models.CharField(
        max_length=20,
        choices=FIELD_TYPE_CHOICES,
        default='text'
    )

    options = models.TextField(
        blank=True,
        help_text=(
            'For dropdown / multiple select: enter options separated by commas.'
        )
    )

    special_key = models.CharField(
        max_length=20,
        choices=SPECIAL_KEY_CHOICES,
        blank=True,
        default='',
        help_text=(
            'Only for Number fields. Use "Minimum/Maximum Guests" so the '
            'value is also used by guest-count search filters.'
        )
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

    is_required = models.BooleanField(default=False)

    order = models.PositiveIntegerField(
        default=0,
        help_text='Controls the display order of this field'
    )

    class Meta:
        ordering = ['order', 'id']

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()

        if (
            self.service_id
            and self.category_id
            and self.service.category_id != self.category_id
        ):
            raise ValidationError({
                'service': (
                    'Selected service must belong to the selected category.'
                )
            })

        if self.special_key and self.field_type != 'number':
            raise ValidationError({
                'special_key': 'Special keys can only be used on Number fields.'
            })

        if self.special_key and self.service_id:
            clash = CategoryAttribute.objects.filter(
                service_id=self.service_id,
                special_key=self.special_key,
            ).exclude(pk=self.pk)

            if clash.exists():
                raise ValidationError({
                    'special_key': 'This service already has an attribute with this special key.'
                })

        if self.field_type in ('dropdown', 'multiselect') and not self.options.strip():
            raise ValidationError({
                'options': 'Please enter options separated by commas.'
            })

    def __str__(self):
        if self.service_id:
            return f'{self.service.name} - {self.label}'

        return f'{self.category.name} - {self.label}'