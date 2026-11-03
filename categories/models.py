
from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.db.models import Q


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    icon = models.ImageField(
        upload_to="category_icons/",
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["display_order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Service(models.Model):
    category = models.ForeignKey(
        Category,
        related_name="services",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        unique_together = ("category", "name")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class CategoryAttribute(models.Model):

    FIELD_TYPE_CHOICES = [
        ("text", "Text"),
        ("number", "Number"),
        ("boolean", "Yes / No"),
        ("dropdown", "Dropdown (single choice)"),
        ("multiselect", "Multiple Select (vendor can pick many)"),
    ]

    SPECIAL_KEY_CHOICES = [
        ("", "None (normal field)"),
        ("min_guests", "Minimum Guests"),
        ("max_guests", "Maximum Guests"),
    ]

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="attributes",
    )

    # Legacy field: kept so existing database records are preserved.
    # New attributes should use services or applies_to_all_services.
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="legacy_attributes",
        null=True,
        blank=True,
        editable=False,
    )

    # New field: admin can assign one attribute to multiple services.
    services = models.ManyToManyField(
        Service,
        related_name="attributes",
        blank=True,
    )

    # If checked, this attribute applies to every service in this category.
    applies_to_all_services = models.BooleanField(
        default=False,
        verbose_name="Apply to all services in this category",
        help_text=(
            "Enable for attributes shared by all services, "
            "such as common facilities."
        ),
    )

    label = models.CharField(
        max_length=150,
        help_text="Example: Seating Capacity",
    )

    field_type = models.CharField(
        max_length=20,
        choices=FIELD_TYPE_CHOICES,
        default="text",
    )

    options = models.TextField(
        blank=True,
        help_text=(
            "For dropdown / multiple select: enter options separated by commas."
        ),
    )

    special_key = models.CharField(
        max_length=20,
        choices=SPECIAL_KEY_CHOICES,
        blank=True,
        default="",
        help_text=(
            'Only for Number fields. Use "Minimum/Maximum Guests" '
            "so the value is also used by guest-count search filters."
        ),
    )

    unit = models.CharField(
        max_length=50,
        blank=True,
        help_text="Example: sq ft, guests, vehicles, hours",
    )

    help_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Small instruction shown to the vendor.",
    )

    is_required = models.BooleanField(default=False)

    order = models.PositiveIntegerField(
        default=0,
        help_text="Controls the display order of this field",
    )

    class Meta:
        ordering = ["order", "id"]

    def clean(self):
        super().clean()

        if self.service_id and self.category_id:
            if self.service.category_id != self.category_id:
                raise ValidationError({
                    "service": (
                        "The legacy service must belong to the selected category."
                    )
                })

        if self.special_key and self.field_type != "number":
            raise ValidationError({
                "special_key": "Special keys can only be used on Number fields."
            })

        if self.field_type in ("dropdown", "multiselect"):
            if not self.options.strip():
                raise ValidationError({
                    "options": "Please enter options separated by commas."
                })

    @classmethod
    def for_service(cls, service_id):
        """
        Return attributes applicable to the selected service:
        1. Attributes applying to all services in the category.
        2. Attributes assigned through the new services M2M field.
        3. Old attributes assigned through the legacy service FK.
        """
        return (
            cls.objects.filter(
                Q(applies_to_all_services=True)
                | Q(services__id=service_id)
                | Q(service_id=service_id)
            )
            .distinct()
            .order_by("order", "id")
        )

    def __str__(self):
        if self.applies_to_all_services:
            return f"{self.category.name} - All services - {self.label}"

        if self.service_id:
            return f"{self.service.name} - {self.label}"

        selected_services = list(self.services.all()[:3])
        if selected_services:
            names = ", ".join(service.name for service in selected_services)
            return f"{self.category.name} - {names} - {self.label}"

        return f"{self.category.name} - {self.label}"
