from django import forms

from accounts.forms import BaseUserRegistrationForm
from accounts.models import User

from .models import NGOProfile


class NGORegistrationForm(BaseUserRegistrationForm):
    organization_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Organization name",
            }
        ),
    )

    def save(self, commit=True):
        user = self._create_user(User.Role.NGO)

        if commit:
            NGOProfile.objects.create(
                user=user,
                organization_name=self.cleaned_data["organization_name"],
            )

        return user
