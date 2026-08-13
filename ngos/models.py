from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class NGOProfile(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING = "PENDING", "Pending approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ngo_profile",
    )

    organization_name = models.CharField(max_length=200)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    place_label = models.CharField(max_length=255, blank=True)
    approval_status = models.CharField(
        max_length=16,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        db_index=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_approved(self):
        return self.approval_status == self.ApprovalStatus.APPROVED

    def approve(self):
        self.approval_status = self.ApprovalStatus.APPROVED
        self.approved_at = timezone.now()

    def clean(self):
        if self.user.role != self.user.Role.NGO:
            raise ValidationError("Only NGO users can have an NGO profile.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.organization_name
