from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
# Create your models here.


class DonorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="donor_profile",
    )
    address = models.TextField()

    def __str__(self):
        return self.user.get_full_name()

    def clean(self):
        # Ensures only users with the donor role can have a donor profile
        super().clean()
        if self.user.role != self.user.Role.DONOR:
            raise ValidationError(
                "Only users with the DONOR role can have a Donorprofile."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
