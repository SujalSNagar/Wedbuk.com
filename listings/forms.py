from django import forms

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
# SERVICE CHECKBOX WIDGET
# =========================================================

class ServiceCheckboxSelectMultiple(
    forms.CheckboxSelectMultiple
):

    def __init__(self, *args, **kwargs):

        self.service_category_map = kwargs.pop(
            'service_category_map',
            {}
        )

        super().__init__(
            *args,
            **kwargs
        )

    def create_option(
        self,
        name,
        value,
        label,
        selected,
        index,
        subindex=None,
        attrs=None
    ):

        option = super().create_option(
            name,
            value,
            label,
            selected,
            index,
            subindex=subindex,
            attrs=attrs
        )

        try:
            service_id = int(value.value)
        except (AttributeError, TypeError, ValueError):
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
        queryset=EventType.objects.filter(
            is_active=True
        ),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.none(),
        required=True,
        widget=ServiceCheckboxSelectMultiple
    )

    class Meta:

        model = Listing

        fields = [
            'category',
            'title',
            'description',
            'base_price',

            'min_guests',
            'max_guests',

            'address_line_1',
            'address_line_2',
            'state',
            'city',
            'pincode',

            'latitude',
            'longitude',

            'cover_image',

            'event_types',
            'services',

            'is_active',
        ]

        widgets = {

            'category': forms.Select(
                attrs={
                    'class': 'form-control'
                }
            ),

            'title': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter listing title'
                }
            ),

            'description': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 6,
                    'placeholder': 'Describe your service...'
                }
            ),

            'base_price': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter starting price',
                    'min': '0',
                    'step': '0.01'
                }
            ),

            'min_guests': forms.NumberInput(
                attrs={
                    'placeholder': 'e.g. 100',
                    'min': '1',
                    'max': '100000',
                    'step': '1',
                }
            ),

            'max_guests': forms.NumberInput(
                attrs={
                    'placeholder': 'e.g. 500',
                    'min': '1',
                    'max': '100000',
                    'step': '1',
                }
            ),

            'address_line_1': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Building / Street / Area'
                }
            ),

            'address_line_2': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Landmark / Additional address'
                }
            ),

            'state': forms.Select(
                attrs={
                    'class': 'form-control',
                    'id': 'id_listing_state'
                }
            ),

            'city': forms.Select(
                attrs={
                    'class': 'form-control',
                    'id': 'id_listing_city'
                }
            ),

            'pincode': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter pincode',
                    'maxlength': '10'
                }
            ),

            'latitude': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Latitude',
                    'step': 'any',
                    'id': 'id_latitude'
                }
            ),

            'longitude': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Longitude',
                    'step': 'any',
                    'id': 'id_longitude'
                }
            ),

            'cover_image': forms.FileInput(
                attrs={
                    'class': 'form-control',
                    'accept': 'image/*'
                }
            ),

            'is_active': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input'
                }
            ),
        }

    def __init__(
        self,
        *args,
        vendor_profile=None,
        **kwargs
    ):

        super().__init__(
            *args,
            **kwargs
        )

        self.vendor_profile = vendor_profile

        # =================================================
        # VENDOR CATEGORIES
        # =================================================

        if vendor_profile:
        
            vendor_categories = (
                vendor_profile.categories
                .filter(
                    is_active=True
                )
                .order_by(
                    'display_order',
                    'name'
                )
            )
        
        else:
        
            vendor_categories = Category.objects.none()
        
        # All active services belonging to
        # vendor's selected categories
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
        self.fields['category'].queryset = (
            vendor_categories
        )

        # =================================================
        # CATEGORY INITIAL VALUE
        # =================================================

        category_id = None

        if self.is_bound:
        
            category_id = self.data.get(
                'category'
            )

            if (
                not category_id
                and vendor_categories.count() == 1
            ):
                category_id = vendor_categories.first().pk

        elif self.instance.pk:

            category_id = self.instance.category_id

        elif vendor_categories.count() == 1:

            only_category = vendor_categories.first()

            self.fields['category'].initial = (
                only_category.pk
            )

            category_id = only_category.pk

        # =================================================
        # LOCK CATEGORY IF VENDOR HAS ONLY ONE
        # =================================================

        if vendor_categories.count() == 1:

            self.fields['category'].disabled = True

        # =================================================
        # EVENT TYPES
        # =================================================

        self.fields['event_types'].queryset = (
            EventType.objects
            .filter(
                is_active=True
            )
            .order_by('name')
        )

        # =================================================
        # SERVICES
        # =================================================

        if vendor_profile:
            service_queryset = vendor_services
        else:
            service_queryset = Service.objects.none()

        service_category_map = {
            service.id: service.category_id
            for service in service_queryset
        }


        self.fields['services'].widget = (
            ServiceCheckboxSelectMultiple(
                service_category_map=service_category_map
            )
        )


        self.fields['services'].queryset = service_queryset



        # =================================================
        # TITLE DEFAULT
        # =================================================

        if (
            category_id
            and not self.instance.pk
        ):

            selected_category = (
                vendor_categories
                .filter(
                    id=category_id
                )
                .first()
            )

            if selected_category:

                self.fields['title'].initial = (
                    selected_category.name
                )

        # =================================================
        # STATES
        # =================================================

        self.fields['state'].queryset = (
            State.objects
            .filter(
                is_active=True
            )
            .order_by('name')
        )

        # =================================================
        # CITY INITIALLY EMPTY
        # =================================================

        self.fields['city'].queryset = (
            City.objects.none()
        )

        # =================================================
        # CITY WHEN FORM IS SUBMITTED
        # =================================================

        if self.is_bound:

            state_id = self.data.get(
                'state'
            )

            if state_id:

                self.fields['city'].queryset = (
                    City.objects
                    .filter(
                        state_id=state_id,
                        is_active=True
                    )
                    .order_by('name')
                )

        # =================================================
        # CITY WHEN EDITING
        # =================================================

        elif (
            self.instance.pk
            and self.instance.state_id
        ):

            self.fields['city'].queryset = (
                City.objects
                .filter(
                    state_id=self.instance.state_id,
                    is_active=True
                )
                .order_by('name')
            )

        # =================================================
        # CATEGORY ATTRIBUTES
        # =================================================

        if category_id:

            attributes = (
                CategoryAttribute.objects
                .filter(
                    category_id=category_id
                )
                .order_by(
                    'order',
                    'id'
                )
            )

            existing_values = {}

            if self.instance.pk:

                existing_values = {
                    item.attribute_id: item.value
                    for item in (
                        self.instance
                        .attribute_values
                        .all()
                    )
                }

            for attribute in attributes:

                field_name = (
                    f'attribute_{attribute.id}'
                )

                field_kwargs = {
                    'required': False,
                    'label': attribute.label,
                    'help_text': attribute.help_text,
                }

                common_attrs = {
                    'class': 'form-control',
                }

                if attribute.field_type == 'text':

                    field = forms.CharField(
                        widget=forms.TextInput(
                            attrs=common_attrs
                        ),
                        **field_kwargs
                    )

                elif attribute.field_type == 'number':

                    field = forms.DecimalField(
                        widget=forms.NumberInput(
                            attrs={
                                **common_attrs,
                                'step': 'any',
                            }
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
                        widget=forms.Select(
                            attrs=common_attrs
                        ),
                        **field_kwargs
                    )

                elif attribute.field_type == 'dropdown':

                    options = []

                    for option in (
                        attribute.options.split(',')
                    ):

                        option = option.strip()

                        if option:

                            options.append(
                                (
                                    option,
                                    option
                                )
                            )

                    field = forms.ChoiceField(
                        choices=[
                            ('', 'Select')
                        ] + options,
                        widget=forms.Select(
                            attrs=common_attrs
                        ),
                        **field_kwargs
                    )

                else:

                    field = forms.CharField(
                        widget=forms.TextInput(
                            attrs=common_attrs
                        ),
                        **field_kwargs
                    )

                # Existing value while editing
                if attribute.id in existing_values:

                    value = existing_values[
                        attribute.id
                    ]

                    if (
                        attribute.field_type
                        == 'boolean'
                    ):

                        if value in [
                            'True',
                            'true',
                            '1'
                        ]:

                            value = 'true'

                        elif value in [
                            'False',
                            'false',
                            '0'
                        ]:

                            value = 'false'

                    field.initial = value

                self.fields[field_name] = field

    def clean(self):

        cleaned_data = super().clean()

        # =================================================
        # CATEGORY VALIDATION
        # =================================================

        category = cleaned_data.get(
            'category'
        )

        if (
            category
            and self.vendor_profile
        ):

            vendor_has_category = (
                self.vendor_profile
                .categories
                .filter(
                    pk=category.pk,
                    is_active=True
                )
                .exists()
            )

            if not vendor_has_category:
            
                self.add_error(
                    'category',
                    'You can only select a category '
                    'from your selected categories.'
                )

        # =================================================
        # SERVICE VALIDATION
        # =================================================

        services = cleaned_data.get(
            'services'
        )

        if (
            category
            and services is not None
            and self.vendor_profile
        ):

            allowed_services = (
                Service.objects
                .filter(
                    category=category,
                    is_active=True
                )
            )

            allowed_service_ids = set(
                allowed_services
                .values_list(
                    'id',
                    flat=True
                )
            )

            selected_service_ids = set(
                services.values_list(
                    'id',
                    flat=True
                )
            )

            invalid_services = (
                selected_service_ids
                - allowed_service_ids
            )

            if invalid_services:

                self.add_error(
                    'services',
                    'Please select only services '
                    'belonging to the selected category.'
                )

        # =================================================
        # STATE / CITY VALIDATION
        # =================================================

        state = cleaned_data.get(
            'state'
        )

        city = cleaned_data.get(
            'city'
        )

        if state and city:

            if city.state_id != state.id:

                self.add_error(
                    'city',
                    'Selected city does not belong '
                    'to selected state.'
                )

        # =================================================
        # GUEST CAPACITY VALIDATION
        # =================================================

        min_guests = cleaned_data.get(
            'min_guests'
        )

        max_guests = cleaned_data.get(
            'max_guests'
        )

        if (
            min_guests is not None
            and max_guests is not None
        ):

            if min_guests > max_guests:

                self.add_error(
                    'max_guests',
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