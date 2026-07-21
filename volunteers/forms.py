from accounts.forms import BaseUserRegistrationForm
from accounts.models import User

from .models import VolunteerProfile


class VolunteerRegistrationForm(BaseUserRegistrationForm):
    def save(self, commit=True):
        user = self._create_user(
            User.Role.VOLUNTEER,
            commit=commit,
        )

        if commit:
            VolunteerProfile.objects.create(
                user=user,
            )

        return user
