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
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"placeholder": "e.g. Bengaluru"}))

    class Meta(BaseUserRegistrationForm.Meta):
        fields = BaseUserRegistrationForm.Meta.fields + ("address", "city")

    def save(self, commit=True):
        user = self._create_user(User.Role.DONOR)

        if commit:
            DonorProfile.objects.create(
                user=user,
                address=self.cleaned_data["address"],
                city=self.cleaned_data["city"],
            )

        return user


class DonorProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=20)
    phone = forms.CharField(max_length=15)

    class Meta:
        model = DonorProfile
        fields = ["address", "city"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["city"].required = True

        self.fields["first_name"].initial = self.user.first_name
        self.fields["last_name"].initial = self.user.last_name
        self.fields["phone"].initial = self.user.phone

    def save(self, commit=True):
        profile = super().save(commit=False)

        self.user.first_name = self.cleaned_data["first_name"]
        self.user.last_name = self.cleaned_data["last_name"]
        self.user.phone = self.cleaned_data["phone"]

        if commit:
            self.user.save()
            profile.save()

        return profile
