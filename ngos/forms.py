from django import forms

from accounts.forms import BaseUserRegistrationForm
from accounts.models import User

from .models import NGOProfile


class NGORegistrationForm(BaseUserRegistrationForm):
    organization_name = forms.CharField(
        max_length=200,
        label="Organization Name",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your organization name",
                "autocomplete": "organization",
            }
        ),
    )

    address = forms.CharField(
        label="Organization Address",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Enter your organization's address",
                "autocomplete": "street-address",
            }
        ),
    )

    class Meta(BaseUserRegistrationForm.Meta):
        fields = BaseUserRegistrationForm.Meta.fields + (
            "organization_name",
            "address",
        )

    def save(self, commit=True):
        user = self._create_user(
            User.Role.NGO,
            commit=commit,
        )

        if commit:
            NGOProfile.objects.create(
                user=user,
                organization_name=self.cleaned_data["organization_name"],
                address=self.cleaned_data["address"],
            )

        return user
