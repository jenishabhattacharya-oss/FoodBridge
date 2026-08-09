from django import forms

from .models import Donation


class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = (
            "title", "description", "food_type", "food_condition", "quantity", "unit",
            "prepared_at", "storage_notes", "allergen_notes", "pickup_address",
            "pickup_window_start", "pickup_window_end",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "storage_notes": forms.Textarea(attrs={"rows": 2}),
            "allergen_notes": forms.Textarea(attrs={"rows": 2}),
            "pickup_address": forms.Textarea(attrs={"rows": 3}),
            "prepared_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "pickup_window_start": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "pickup_window_end": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class NGOReceiptForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ("receipt_photo",)

    def clean_receipt_photo(self):
        photo = self.cleaned_data.get("receipt_photo")
        if not photo:
            raise forms.ValidationError("A proof photo is required to confirm receipt.")
        return photo
