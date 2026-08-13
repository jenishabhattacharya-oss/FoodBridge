from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class VolunteerProfile(models.Model):
    class TransportMode(models.TextChoices):
        WALKING = "WALKING", "Walking"
        BICYCLE = "BICYCLE", "Bicycle"
        MOTORCYCLE = "MOTORCYCLE", "Motorcycle"
        CAR = "CAR", "Car"
        OTHER = "OTHER", "Other"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="volunteer_profile",
    )
    service_area = models.CharField(max_length=100, blank=True)
    transport_mode = models.CharField(
        max_length=20,
        choices=TransportMode.choices,
        default=TransportMode.WALKING,
    )
    is_available = models.BooleanField(default=True)
    location_sharing_consent = models.BooleanField(default=False)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} (Volunteer)"

    def clean(self):
        super().clean()

        if self.user.role != self.user.Role.VOLUNTEER:
            raise ValidationError(
                "Only users with the VOLUNTEER role can have a VolunteerProfile."
            )

    def save(self, *args, **kwargs):
        if not self.is_available:
            self.current_latitude = None
            self.current_longitude = None
            self.location_updated_at = None
        self.full_clean()
        super().save(*args, **kwargs)


class Pickup(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLAIMED = "CLAIMED", "Claimed"
        COLLECTED = "COLLECTED", "Collected"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    donor_name = models.CharField(max_length=200)
    donor_phone = models.CharField(max_length=15)
    pickup_address = models.TextField()
    pickup_city = models.CharField(max_length=100)
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_place_label = models.CharField(max_length=255, blank=True)
    food_description = models.CharField(max_length=255)
    quantity = models.CharField(max_length=100)
    pickup_window_start = models.DateTimeField()
    pickup_window_end = models.DateTimeField()
    instructions = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    assigned_volunteer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_pickups",
        null=True,
        blank=True,
    )
    claimed_at = models.DateTimeField(null=True, blank=True)
    collected_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    recipient_name = models.CharField(max_length=200, blank=True)
    recipient_address = models.TextField(blank=True)
    destination_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_place_label = models.CharField(max_length=255, blank=True)
    handoff_notes = models.TextField(blank=True)
    delivery_photo = models.ImageField(upload_to="delivery_proofs/%Y/%m/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("pickup_window_start", "id")
        indexes = [
            models.Index(
                fields=("status", "pickup_city", "pickup_window_start"),
                name="pickup_open_city_time_idx",
            ),
            models.Index(
                fields=("assigned_volunteer", "status"),
                name="pickup_volunteer_status_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("assigned_volunteer",),
                condition=models.Q(status__in=("CLAIMED", "COLLECTED")),
                name="one_active_pickup_per_volunteer",
            )
        ]

    def __str__(self):
        return f"{self.donor_name} — {self.food_description}"

    def clean(self):
        super().clean()
        if self.pickup_window_end <= self.pickup_window_start:
            raise ValidationError(
                {"pickup_window_end": "The pickup window must end after it starts."}
            )

        if self.assigned_volunteer and self.assigned_volunteer.role != self.assigned_volunteer.Role.VOLUNTEER:
            raise ValidationError({"assigned_volunteer": "The assignee must be a volunteer."})

        if self.status == self.Status.OPEN and self.assigned_volunteer:
            raise ValidationError({"assigned_volunteer": "Open pickups cannot have an assignee."})
        if self.status in (self.Status.CLAIMED, self.Status.COLLECTED, self.Status.DELIVERED) and not self.assigned_volunteer:
            raise ValidationError({"assigned_volunteer": "This pickup needs an assigned volunteer."})
        if self.status == self.Status.DELIVERED:
            required = {
                "recipient_name": self.recipient_name,
                "recipient_address": self.recipient_address,
                "delivery_photo": self.delivery_photo,
                "delivered_at": self.delivered_at,
            }
            missing = [field for field, value in required.items() if not value]
            if missing:
                raise ValidationError(
                    {field: "This field is required when a pickup is delivered." for field in missing}
                )

    def mark_claimed(self, volunteer):
        self.status = self.Status.CLAIMED
        self.assigned_volunteer = volunteer
        self.claimed_at = timezone.now()

    def mark_collected(self):
        self.status = self.Status.COLLECTED
        self.collected_at = timezone.now()

    def mark_delivered(self):
        self.status = self.Status.DELIVERED
        self.delivered_at = timezone.now()
