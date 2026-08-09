from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Donation(models.Model):
    class FoodType(models.TextChoices):
        VEG = "VEG", "Vegetarian"
        NON_VEG = "NON_VEG", "Non-vegetarian"
        BAKERY = "BAKERY", "Bakery"
        GROCERIES = "GROCERIES", "Groceries"
        FRUITS = "FRUITS", "Fruits"
        VEGETABLES = "VEGETABLES", "Vegetables"

    class FoodCondition(models.TextChoices):
        COOKED = "COOKED", "Cooked"
        FRESH = "FRESH", "Fresh"
        PACKAGED = "PACKAGED", "Packaged"

    class Unit(models.TextChoices):
        KG = "KG", "kg"
        PACKS = "PACKS", "packs"
        PLATES = "PLATES", "plates"
        BOXES = "BOXES", "boxes"

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        VOLUNTEER_CLAIMED = "VOLUNTEER_CLAIMED", "Volunteer claimed"
        IN_TRANSIT = "IN_TRANSIT", "In transit"
        DELIVERED = "DELIVERED", "Delivered"
        NGO_MANAGED = "NGO_MANAGED", "NGO managed"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    donor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="donations")
    title = models.CharField(max_length=120)
    description = models.TextField()
    food_type = models.CharField(max_length=20, choices=FoodType.choices)
    food_condition = models.CharField(max_length=20, choices=FoodCondition.choices)
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=20, choices=Unit.choices)
    prepared_at = models.DateTimeField()
    storage_notes = models.TextField(blank=True)
    allergen_notes = models.TextField(blank=True)
    pickup_address = models.TextField()
    pickup_window_start = models.DateTimeField()
    pickup_window_end = models.DateTimeField()
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.AVAILABLE, db_index=True)
    pickup = models.OneToOneField("volunteers.Pickup", on_delete=models.SET_NULL, null=True, blank=True, related_name="donation")
    claimed_by_ngo = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_donations")
    receipt_photo = models.ImageField(upload_to="ngo_receipts/%Y/%m/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self):
        return f"{self.title} — {self.donor.get_full_name()}"

    @property
    def is_expired(self):
        return self.status == self.Status.AVAILABLE and self.pickup_window_end <= timezone.now()

    @property
    def effective_status(self):
        return self.Status.EXPIRED if self.is_expired else self.status

    @property
    def effective_status_display(self):
        return self.Status(self.effective_status).label

    @property
    def can_be_changed(self):
        return self.status == self.Status.AVAILABLE and not self.is_expired

    def clean(self):
        super().clean()
        if self.pickup_window_end <= self.pickup_window_start:
            raise ValidationError({"pickup_window_end": "The pickup window must end after it starts."})
        if self.prepared_at > self.pickup_window_end:
            raise ValidationError({"prepared_at": "Preparation time must be before pickup ends."})
        if self.donor_id and self.donor.role != self.donor.Role.DONOR:
            raise ValidationError({"donor": "Only donors can create donations."})
