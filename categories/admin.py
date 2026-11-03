from django import forms
from django.contrib import admin

from .models import Category, Service, CategoryAttribute


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1
    prepopulated_fields = {
        "slug": ("name",),
    }


class ServiceCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """Adds data-category-* attributes so JS can group the checkboxes."""

    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex, attrs
        )
        instance = getattr(value, "instance", None)
        if instance is not None:
            option["attrs"]["data-category-id"] = str(instance.category_id)
            option["attrs"]["data-category-name"] = instance.category.name
        return option


class CategoryAttributeAdminForm(forms.ModelForm):
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.select_related("category").order_by(
            "category__display_order",
            "category__name",
            "display_order",
            "name",
        ),
        required=False,
        widget=ServiceCheckboxSelectMultiple(),
        label="Services",
        help_text=(
            "You can choose any service of the category "
            "'Apply to all' all category and services "
            "select automatically"
        ),
    )

    class Meta:
        model = CategoryAttribute
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["applies_to_all_services"].help_text = (
            "apply to all categories and their services "
            ""
        )

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("applies_to_all_services"):
            cleaned_data["services"] = Service.objects.none()

        return cleaned_data


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "display_order", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ServiceInline]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "display_order", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["name", "category__name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(CategoryAttribute)
class CategoryAttributeAdmin(admin.ModelAdmin):
    form = CategoryAttributeAdminForm

    list_display = [
        "label",
        "category",
        "attribute_scope",
        "field_type",
        "is_required",
        "order",
    ]

    list_filter = [
        "category",
        "applies_to_all_services",
        "field_type",
        "is_required",
    ]

    search_fields = [
        "label",
        "category__name",
        "services__name",
    ]

    fields = [
        "category",
        "applies_to_all_services",
        "services",
        "label",
        "field_type",
        "options",
        "special_key",
        "unit",
        "help_text",
        "is_required",
        "order",
    ]

    class Media:
        js = ("js/attribute-admin.js",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("category", "service")
            .prefetch_related("services")
        )

    @admin.display(description="Applies to")
    def attribute_scope(self, obj):
        if obj.applies_to_all_services:
            return "All services (all categories)"

        names = [s.name for s in obj.services.all()]

        if obj.service_id and obj.service.name not in names:
            names.append(obj.service.name)

        return ", ".join(names) if names else "No services selected"