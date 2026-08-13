from django import forms

from .models import VolunteerPayoutProfile


class VolunteerPayoutProfileForm(forms.Form):
    destination = forms.ChoiceField(choices=VolunteerPayoutProfile.Destination.choices)
    upi_id = forms.CharField(required=False, max_length=100)
    account_holder = forms.CharField(required=False, max_length=120)
    account_number = forms.CharField(required=False, max_length=40)
    ifsc = forms.CharField(required=False, max_length=20)

    def clean(self):
        data = super().clean()
        if data.get("destination") == VolunteerPayoutProfile.Destination.UPI and not data.get("upi_id"):
            self.add_error("upi_id", "Enter a UPI ID.")
        if data.get("destination") == VolunteerPayoutProfile.Destination.BANK:
            for field in ("account_holder", "account_number", "ifsc"):
                if not data.get(field): self.add_error(field, "This field is required for a bank payout.")
        return data
