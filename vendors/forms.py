from django import forms

from .models import VendorProfile
from categories.models import Category
from locations.models import State, City


class VendorOnboardingForm(forms.ModelForm):

    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.filter(
            is_active=True
        ).order_by(
            'display_order',
            'name'
        ),
        required=True,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = VendorProfile

        fields = [
            'business_name',
            'state',
            'city',
            'categories',
        ]

        widgets = {
            'business_name': forms.TextInput(
                attrs={
                    'placeholder': 'Enter your business name'
                }
            ),

            'state': forms.Select(
                attrs={
                    'id': 'id_state'
                }
            ),

            'city': forms.Select(
                attrs={
                    'id': 'id_city'
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # State and City are nullable in the database
        # because vendor profile is created during registration.
        # But they are required during onboarding.

        self.fields['state'].required = True
        self.fields['city'].required = True

        self.fields['state'].queryset = State.objects.filter(
            is_active=True
        )

        self.fields['city'].queryset = City.objects.none()

        if self.is_bound:
            state_id = self.data.get('state')

            if state_id:
                self.fields['city'].queryset = City.objects.filter(
                    state_id=state_id,
                    is_active=True
                )

        elif self.instance.pk and self.instance.state_id:
            self.fields['city'].queryset = City.objects.filter(
                state=self.instance.state,
                is_active=True
            )