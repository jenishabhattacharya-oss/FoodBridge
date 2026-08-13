from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Donation(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending verification"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        HUMAN_REVIEW = "HUMAN_REVIEW", "Awaiting human review"
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
        NGO_ACCEPTED = "NGO_ACCEPTED", "NGO accepted"
        VOLUNTEER_CLAIMED = "VOLUNTEER_CLAIMED", "Volunteer claimed"
        IN_TRANSIT = "IN_TRANSIT", "In transit"
        AWAITING_NGO_CONFIRMATION = "AWAITING_NGO_CONFIRMATION", "Awaiting NGO confirmation"
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
    is_unpackaged = models.BooleanField(default=False)
    food_photo_overview = models.ImageField(upload_to="donation_photos/%Y/%m/", blank=True)
    food_photo_closeup = models.ImageField(upload_to="donation_photos/%Y/%m/", blank=True)
    food_photo_label = models.ImageField(upload_to="donation_photos/%Y/%m/", blank=True)
    verification_status = models.CharField(max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.PENDING, db_index=True)
    verification_summary = models.TextField(blank=True)
    verification_confidence = models.PositiveSmallIntegerField(null=True, blank=True)
    visible_risk_flags = models.JSONField(default=list, blank=True)
    verification_provider = models.CharField(max_length=40, blank=True)
    verification_model = models.CharField(max_length=100, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="food_reviews")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    pickup_address = models.TextField()
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_place_label = models.CharField(max_length=255, blank=True)
    pickup_window_start = models.DateTimeField()
    pickup_window_end = models.DateTimeField()
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.AVAILABLE, db_index=True)
    pickup = models.OneToOneField("volunteers.Pickup", on_delete=models.SET_NULL, null=True, blank=True, related_name="donation")
    claimed_by_ngo = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_donations")
    receiving_ngo = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="volunteer_deliveries", limit_choices_to={"role": "NGO"})
    receipt_photo = models.ImageField(upload_to="ngo_receipts/%Y/%m/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("status", "pickup_window_end"), name="donation_active_idx"),
            models.Index(fields=("claimed_by_ngo", "status"), name="donation_ngo_status_idx"),
        ]

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
        return (
            self.status == self.Status.AVAILABLE and not self.is_expired
        ) or (
            not self.pickup_id and self.verification_status in (self.VerificationStatus.REJECTED, self.VerificationStatus.HUMAN_REVIEW)
        )

    def clean(self):
        super().clean()
        if self.pickup_window_end <= self.pickup_window_start:
            raise ValidationError({"pickup_window_end": "The pickup window must end after it starts."})
        if self.prepared_at > self.pickup_window_end:
            raise ValidationError({"prepared_at": "Preparation time must be before pickup ends."})
        if self.donor_id and self.donor.role != self.donor.Role.DONOR:
            raise ValidationError({"donor": "Only donors can create donations."})
