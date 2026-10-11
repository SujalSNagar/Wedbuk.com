from django import forms


class BookingForm(forms.Form):

    start_date = forms.DateField(
        required=True,
        input_formats=["%Y-%m-%d"],
    )

    end_date = forms.DateField(
        required=True,
        input_formats=["%Y-%m-%d"],
    )

    guest_count = forms.IntegerField(
        min_value=1,
        required=True,
    )

    customer_note = forms.CharField(
        required=False,
        max_length=2000,
        widget=forms.Textarea,
    )

    full_name = forms.CharField(
        max_length=150,
        required=True,
    )

    phone_number = forms.CharField(
        max_length=15,
        required=True,
    )

    email = forms.EmailField(
        required=True,
    )

    def __init__(self, *args, listing=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.listing = listing

    def clean_guest_count(self):

        guest_count = self.cleaned_data["guest_count"]

        if guest_count < 1:
            raise forms.ValidationError(
                "Number of guests must be at least 1."
            )

        if (
            self.listing
            and self.listing.max_guests is not None
            and guest_count > self.listing.max_guests
        ):
            raise forms.ValidationError(
                f"You can enter maximum "
                f"{self.listing.max_guests} guests."
            )

        return guest_count

    def clean(self):

        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError(
                "End date cannot be before start date."
            )

        return cleaned_data