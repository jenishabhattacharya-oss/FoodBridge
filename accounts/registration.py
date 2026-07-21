from accounts.models import User

from donors.forms import DonorRegistrationForm
from volunteers.forms import VolunteerRegistrationForm
from ngos.forms import NGORegistrationForm


ROLE_REGISTRY = {
    User.Role.DONOR: {
        "label": "Donor",
        "description": "Donate surplus food",
        "form": DonorRegistrationForm,
    },
    User.Role.VOLUNTEER: {
        "label": "Volunteer",
        "description": "Help deliver food",
        "form": VolunteerRegistrationForm,
    },
    User.Role.NGO: {
        "label": "NGO",
        "description": "Receive donations",
        "form": NGORegistrationForm,
    },
}
