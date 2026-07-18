from django import forms

from accounts.forms import BaseUserRegistrationForm
from accounts.models import User

from .models import DonorProfile


class DonorRegistrationForm(BaseUserRegistrationForm):
    address = forms.CharField(
        label="Pickup Address",
        widget=forms.Textarea(
            attrs={
                "placeholder": "Enter your pickup address",
                "rows": 4,
                "autocomplete": "street-address",
            }
        ),
    )

    class Meta(BaseUserRegistrationForm.Meta):
        fields = BaseUserRegistrationForm.Meta.fields + ("address",)

    def save(self, commit=True):
        user = self._create_user(User.Role.DONOR)

        if commit:
            DonorProfile.objects.create(
                user=user,
                address=self.cleaned_data["address"],
            )

        return user
