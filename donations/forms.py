from django import forms
from django.conf import settings

from .models import Donation


class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = (
            "title", "description", "food_type", "food_condition", "quantity", "unit",
            "prepared_at", "storage_notes", "allergen_notes", "is_unpackaged",
            "food_photo_overview", "food_photo_closeup", "food_photo_label", "pickup_address",
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

    def clean(self):
        cleaned = super().clean()
        max_size = settings.FOOD_PHOTO_MAX_SIZE_BYTES
        for field in ("food_photo_overview", "food_photo_closeup", "food_photo_label"):
            photo = cleaned.get(field)
            label_is_optional = field == "food_photo_label" and cleaned.get("is_unpackaged")
            if not photo:
                if not label_is_optional:
                    self.add_error(field, "This photo is required for visual food screening.")
            elif photo.size > max_size:
                self.add_error(field, f"Photo must be at most {max_size // 1024 // 1024} MB.")
        return cleaned


class NGOReceiptForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ("receipt_photo",)

    def clean_receipt_photo(self):
        photo = self.cleaned_data.get("receipt_photo")
        if not photo:
            raise forms.ValidationError("A proof photo is required to confirm receipt.")
        return photo
