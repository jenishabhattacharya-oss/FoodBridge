from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class NGOProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ngo_profile",
    )

    organization_name = models.CharField(max_length=200)
    address = models.TextField(default="")

    def clean(self):
        if self.user.role != self.user.Role.NGO:
            raise ValidationError("Only NGO users can have an NGO profile.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.organization_name
