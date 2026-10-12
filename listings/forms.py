from django import forms
from django.db.models import Q

from categories.models import (
    Category,
    CategoryAttribute,
    Service,
)
from core.models import EventType
from locations.models import State, City

from .models import (
    Listing,
    ListingImage,
    ListingAvailability,
    ListingBlockedDate,
)


# =========================================================
# SERVICE SELECT WIDGET
# (adds data-category-id on every <option> so JS can filter)
# =========================================================

class ServiceSelect(forms.Select):

    def __init__(self, *args, **kwargs):
        self.service_category_map = kwargs.pop(
            'service_category_map', {}
        )
        super().__init__(*args, **kwargs)

    def create_option(
        self, name, value, label, selected, index,
        subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index,
            subindex=subindex, attrs=attrs
        )

        try:
            service_id = int(getattr(value, 'value', value))
        except (TypeError, ValueError):
            service_id = None

        if service_id in self.service_category_map:
            option['attrs']['data-category-id'] = str(
                self.service_category_map[service_id]
            )

        return option


# =========================================================
# LISTING FORM
# =========================================================

class ListingForm(forms.ModelForm):

    event_types = forms.ModelMultipleChoiceField(
        queryset=EventType.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    # ONE service per listing
    service = forms.ModelChoiceField(
        queryset=Service.objects.none(),
        required=True,
        empty_label='Select service',
        widget=ServiceSelect(
            attrs={'class': 'form-control', 'id': 'id_service'}
        )
    )

    class Meta:

        model = Listing

        # min_guests / max_guests removed: they now come from
        # service attributes (special_key) and are synced on save.
        fields = [
            'category',
            'service',
            'title',
            'description',
            'base_price',

            'address_line_1',
            'address_line_2',
            'state',
            'city',
            'pincode',

            'latitude',
            'longitude',

            'cover_image',

            'event_types',

            'is_active',
        ]

        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),

            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter listing title'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Describe your service...'
            }),

            'base_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter starting price',
                'min': '0',
                'step': '0.01'
            }),

            'address_line_1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Building / Street / Area'
            }),

            'address_line_2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Landmark / Additional address'
            }),

            'state': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_listing_state'
            }),

            'city': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_listing_city'
            }),

            'pincode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter pincode',
                'maxlength': '10'
            }),

            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Latitude',
                'step': 'any',
                'id': 'id_latitude'
            }),

            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Longitude',
                'step': 'any',
                'id': 'id_longitude'
            }),

            'cover_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),

            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, vendor_profile=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.vendor_profile = vendor_profile

        # attribute_id -> special_key (min_guests / max_guests)
        self.special_attribute_fields = {}

        # =================================================
        # VENDOR CATEGORIES
        # =================================================

        if vendor_profile:
            vendor_categories = (
                vendor_profile.categories
                .filter(is_active=True)
                .order_by('display_order', 'name')
            )
        else:
            vendor_categories = Category.objects.none()

        if vendor_categories.exists():
            vendor_services = (
                Service.objects
                .filter(
                    category__in=vendor_categories,
                    is_active=True
                )
                .select_related('category')
                .order_by(
                    'category__display_order',
                    'display_order',
                    'name'
                )
            )
        else:
            vendor_services = Service.objects.none()

        self.fields['category'].queryset = vendor_categories

        # =================================================
        # CATEGORY INITIAL VALUE
        # =================================================

        category_id = None

        if self.is_bound:
            category_id = self.data.get('category')

            if (
                not category_id
                and vendor_categories.count() == 1
            ):
                category_id = vendor_categories.first().pk

        elif self.instance.pk:
            category_id = self.instance.category_id

        elif vendor_categories.count() == 1:
            only_category = vendor_categories.first()
            self.fields['category'].initial = only_category.pk
            category_id = only_category.pk

        if vendor_categories.count() == 1:
            self.fields['category'].disabled = True

        # =================================================
        # EVENT TYPES
        # =================================================

        self.fields['event_types'].queryset = (
            EventType.objects
            .filter(is_active=True)
            .order_by('name')
        )

        # =================================================
        # SERVICE (single select)
        # =================================================

        service_category_map = {
            service.id: service.category_id
            for service in vendor_services
        }

        self.fields['service'].widget = ServiceSelect(
            attrs={'class': 'form-control', 'id': 'id_service'},
            service_category_map=service_category_map
        )
        self.fields['service'].queryset = vendor_services
        # show only "Banquet Hall" instead of "Venue - Banquet Hall"
        self.fields['service'].label_from_instance = (
            lambda obj: obj.name
        )

        # =================================================
        # TITLE DEFAULT
        # =================================================

        if category_id and not self.instance.pk:
            selected_category = (
                vendor_categories.filter(id=category_id).first()
            )

            if selected_category:
                self.fields['title'].initial = selected_category.name

        # =================================================
        # STATES / CITIES
        # =================================================

        self.fields['state'].queryset = (
            State.objects.filter(is_active=True).order_by('name')
        )

        self.fields['city'].queryset = City.objects.none()

        if self.is_bound:
            state_id = self.data.get('state')

            if state_id:
                self.fields['city'].queryset = (
                    City.objects
                    .filter(state_id=state_id, is_active=True)
                    .order_by('name')
                )

        elif self.instance.pk and self.instance.state_id:
            self.fields['city'].queryset = (
                City.objects
                .filter(
                    state_id=self.instance.state_id,
                    is_active=True
                )
                .order_by('name')
            )

        # =================================================
        # SERVICE ATTRIBUTES
        # Only attributes created for the SELECTED service.
        # =================================================

        service_id = None

        if self.is_bound:
            service_id = self.data.get('service')
        elif self.instance.pk:
            service_id = self.instance.service_id

        try:
            service_id = int(service_id) if service_id else None
        except (TypeError, ValueError):
            service_id = None

        if category_id and service_id:

            attributes = (
                CategoryAttribute.objects
                .filter(
                    category_id=category_id,
                    service_id=service_id
                )
                .order_by('order', 'id')
            )

            existing_values = {}

            if self.instance.pk:
                existing_values = {
                    item.attribute_id: item.value
                    for item in self.instance.attribute_values.all()
                }

            for attribute in attributes:
                field_name = f'attribute_{attribute.id}'

                field_kwargs = {
                    'required': attribute.is_required,
                    'label': attribute.label,
                    'help_text': attribute.help_text,
                }

                common_attrs = {'class': 'form-control'}

                options = [
                    (option.strip(), option.strip())
                    for option in (attribute.options or '').split(',')
                    if option.strip()
                ]

                if attribute.field_type == 'number':
                    field = forms.DecimalField(
                        min_value=0,
                        widget=forms.NumberInput(
                            attrs={**common_attrs, 'step': 'any'}
                        ),
                        **field_kwargs
                    )

                elif attribute.field_type == 'boolean':
                    field = forms.ChoiceField(
                        choices=[
                            ('', 'Select'),
                            ('true', 'Yes'),
                            ('false', 'No'),
                        ],
                        widget=forms.Select(attrs=common_attrs),
                        **field_kwargs
                    )

                elif attribute.field_type == 'dropdown':
                    field = forms.ChoiceField(
                        choices=[('', 'Select')] + options,
                        widget=forms.Select(attrs=common_attrs),
                        **field_kwargs
                    )

                elif attribute.field_type == 'multiselect':
                    field = forms.MultipleChoiceField(
                        choices=options,
                        widget=forms.CheckboxSelectMultiple,
                        **field_kwargs
                    )

                else:
                    field = forms.CharField(
                        widget=forms.TextInput(attrs=common_attrs),
                        **field_kwargs
                    )

                if attribute.id in existing_values:
                    value = existing_values[attribute.id]

                    if attribute.field_type == 'boolean':
                        if value in ['True', 'true', '1']:
                            value = 'true'
                        elif value in ['False', 'false', '0']:
                            value = 'false'

                    elif attribute.field_type == 'multiselect':
                        value = [
                            item.strip()
                            for item in value.split(',')
                            if item.strip()
                        ]

                    field.initial = value

                self.fields[field_name] = field

                if attribute.special_key:
                    self.special_attribute_fields[
                        field_name
                    ] = attribute.special_key

    # =====================================================
    # VALUES FOR Listing.min_guests / Listing.max_guests
    # =====================================================

    def get_special_values(self):
        """{'min_guests': int|None, 'max_guests': int|None}"""

        result = {'min_guests': None, 'max_guests': None}

        for field_name, key in self.special_attribute_fields.items():
            value = self.cleaned_data.get(field_name)

            if value not in (None, ''):
                result[key] = int(value)

        return result

    # =====================================================
    # VALIDATION
    # =====================================================

    def clean(self):
        cleaned_data = super().clean()

        category = cleaned_data.get('category')
        service = cleaned_data.get('service')

        if category and self.vendor_profile:
            vendor_has_category = (
                self.vendor_profile.categories
                .filter(pk=category.pk, is_active=True)
                .exists()
            )

            if not vendor_has_category:
                self.add_error(
                    'category',
                    'You can only select a category '
                    'from your selected categories.'
                )

        if category and service and service.category_id != category.id:
            self.add_error(
                'service',
                'Please select a service belonging '
                'to the selected category.'
            )

        state = cleaned_data.get('state')
        city = cleaned_data.get('city')

        if state and city and city.state_id != state.id:
            self.add_error(
                'city',
                'Selected city does not belong to selected state.'
            )

        # Guest capacity (from special attributes)
        special = {}

        for field_name, key in self.special_attribute_fields.items():
            value = cleaned_data.get(field_name)

            if value not in (None, ''):
                special[key] = (field_name, value)

        if 'min_guests' in special and 'max_guests' in special:
            if special['min_guests'][1] > special['max_guests'][1]:
                self.add_error(
                    special['max_guests'][0],
                    'Maximum guests cannot be less '
                    'than minimum guests.'
                )

        return cleaned_data


# =========================================================
# LISTING IMAGE FORM
# =========================================================

class ListingImageForm(forms.ModelForm):

    class Meta:

        model = ListingImage

        fields = [
            'image',
            'display_order',
        ]

        widgets = {
            'image': forms.ClearableFileInput(
                attrs={
                    'accept': 'image/*'
                }
            ),

            'display_order': forms.NumberInput(
                attrs={
                    'min': '0'
                }
            ),
        }


# =========================================================
# LISTING AVAILABILITY FORM
# =========================================================

class ListingAvailabilityForm(forms.ModelForm):

    class Meta:

        model = ListingAvailability

        fields = [
            'available_from',
            'available_until',
            'is_active',
        ]

        widgets = {

            'available_from': forms.DateInput(
                attrs={
                    'type': 'date'
                }
            ),

            'available_until': forms.DateInput(
                attrs={
                    'type': 'date'
                }
            ),

            'is_active': forms.CheckboxInput(),
        }

    def clean(self):

        cleaned_data = super().clean()

        available_from = cleaned_data.get(
            'available_from'
        )

        available_until = cleaned_data.get(
            'available_until'
        )

        if (
            available_from
            and available_until
            and available_from > available_until
        ):

            raise forms.ValidationError(
                'Available until date cannot be '
                'before available from date.'
            )

        return cleaned_data


# =========================================================
# LISTING BLOCKED DATE FORM
# =========================================================

class ListingBlockedDateForm(forms.ModelForm):

    class Meta:

        model = ListingBlockedDate

        fields = [
            'date',
            'reason',
        ]

        widgets = {

            'date': forms.DateInput(
                attrs={
                    'type': 'date'
                }
            ),

            'reason': forms.TextInput(
                attrs={
                    'placeholder': 'Optional reason'
                }
            ),
        }