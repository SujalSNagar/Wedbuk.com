from django import forms

from .models import User


class RegisterForm(forms.Form):

    full_name = forms.CharField(
        max_length=150,
        required=True
    )

    email = forms.EmailField(
        required=True
    )

    phone_number = forms.CharField(
        min_length=10,
        max_length=10,
        required=True,
        widget=forms.TextInput(
            attrs={
                'inputmode': 'numeric',
                'maxlength': '10',
                'pattern': '[0-9]{10}',
                'placeholder': 'Enter 10-digit mobile number'
            }
        )
    )

    password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput
    )

    confirm_password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput
    )

    def clean_full_name(self):

        full_name = self.cleaned_data['full_name'].strip()

        if not full_name:
            raise forms.ValidationError(
                'Full name is required.'
            )

        return full_name

    def clean_email(self):

        email = self.cleaned_data['email'].strip().lower()

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                'An account with this email already exists.'
            )

        return email

    def clean_phone_number(self):

        phone_number = self.cleaned_data['phone_number'].strip()

        if User.objects.filter(
            phone_number=phone_number
        ).exists():
            raise forms.ValidationError(
                'An account with this phone number already exists.'
            )

        return phone_number

    def clean(self):

        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if (
            password
            and confirm_password
            and password != confirm_password
        ):
            raise forms.ValidationError(
                'Passwords do not match.'
            )

        return cleaned_data


class VendorRegisterForm(forms.Form):

    business_name = forms.CharField(
        max_length=200,
        required=True,
        label='Business Name'
    )

    full_name = forms.CharField(
        max_length=150,
        required=True
    )

    email = forms.EmailField(
        required=True
    )

    phone_number = forms.CharField(
        min_length=10,
        max_length=10,
        required=True,
        widget=forms.TextInput(
            attrs={
                'inputmode': 'numeric',
                'maxlength': '10',
                'pattern': '[0-9]{10}',
                'placeholder': 'Enter 10-digit mobile number'
            }
        )
    )

    password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput
    )

    confirm_password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput
    )

    def clean_business_name(self):

        business_name = self.cleaned_data[
            'business_name'
        ].strip()

        if not business_name:
            raise forms.ValidationError(
                'Business name is required.'
            )

        return business_name

    def clean_email(self):

        email = self.cleaned_data['email'].strip().lower()

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                'An account with this email already exists.'
            )

        return email

    def clean_phone_number(self):

        phone_number = self.cleaned_data['phone_number'].strip()

        if not phone_number.isdigit():
            raise forms.ValidationError(
                'Mobile number must contain only digits.'
            )

        if len(phone_number) != 10:
            raise forms.ValidationError(
                'Mobile number must be exactly 10 digits.'
            )

        if User.objects.filter(
            phone_number=phone_number
        ).exists():
            raise forms.ValidationError(
                'An account with this phone number already exists.'
            )

        return phone_number

    
    def clean(self):

        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if (
            password
            and confirm_password
            and password != confirm_password
        ):
            raise forms.ValidationError(
                'Passwords do not match.'
            )

        return cleaned_data


class LoginForm(forms.Form):

    email = forms.EmailField(
        required=True
    )

    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput
    )

    def __init__(self, *args, **kwargs):

        self.request = kwargs.pop(
            'request',
            None
        )

        super().__init__(*args, **kwargs)

    def clean(self):

        cleaned_data = super().clean()

        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:

            try:
                user = User.objects.get(
                    email=email
                )

                if not user.check_password(password):
                    raise forms.ValidationError(
                        'Invalid email or password.'
                    )

                if not user.is_active:
                    raise forms.ValidationError(
                        'This account is inactive.'
                    )

                cleaned_data['user'] = user

            except User.DoesNotExist:

                raise forms.ValidationError(
                    'Invalid email or password.'
                )

        return cleaned_data