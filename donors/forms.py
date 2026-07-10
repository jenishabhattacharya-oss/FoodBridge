from django import forms
from django.db import transaction

from accounts.forms import BaseUserRegistrationForm
from accounts.models import User

from .models import DonorProfile


class DonorRegistrationForm(BaseUserRegistrationForm):
    address = forms.CharField(widget=forms.Textarea())

    def save(self, commit=True):
        with transaction.atomic():
            user = self._create_user(role=User.Role.DONOR)

            DonorProfile.objects.create(
                user=user,
                address=self.cleaned_data["address"],
            )
            return user
