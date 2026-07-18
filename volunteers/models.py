from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class VolunteerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="volunteer_profile",
    )

    def __str__(self):
        return f"{self.user.get_full_name()} (Volunteer)"

    def clean(self):
        super().clean()

        if self.user.role != self.user.Role.VOLUNTEER:
            raise ValidationError(
                "Only users with the VOLUNTEER role can have a VolunteerProfile."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
