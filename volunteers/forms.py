from django import forms

from accounts.forms import BaseUserRegistrationForm
from accounts.models import User

from .models import Pickup, VolunteerProfile


class VolunteerRegistrationForm(BaseUserRegistrationForm):
    def save(self, commit=True):
        user = self._create_user(
            User.Role.VOLUNTEER,
            commit=commit,
        )

        if commit:
            VolunteerProfile.objects.create(
                user=user,
            )

        return user


class VolunteerProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=20)
    phone = forms.CharField(max_length=15)

    class Meta:
        model = VolunteerProfile
        fields = ("service_area", "transport_mode", "is_available", "location_sharing_consent")
        widgets = {
            "service_area": forms.TextInput(attrs={"placeholder": "e.g. Bengaluru"}),
        }

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name
        self.fields["phone"].initial = user.phone

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data["first_name"]
        self.user.last_name = self.cleaned_data["last_name"]
        self.user.phone = self.cleaned_data["phone"]
        if commit:
            self.user.save()
            profile.save()
        return profile


class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Pickup
        fields = ("recipient_name", "recipient_address", "handoff_notes", "delivery_photo")
        widgets = {
            "recipient_address": forms.Textarea(attrs={"rows": 3}),
            "handoff_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        for field in ("recipient_name", "recipient_address", "delivery_photo"):
            if not cleaned_data.get(field):
                self.add_error(field, "This field is required to confirm delivery.")
        return cleaned_data
