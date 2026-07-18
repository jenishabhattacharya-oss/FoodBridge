from donors.forms import DonorRegistrationForm
from ngos.forms import NGORegistrationForm
from volunteers.forms import VolunteerRegistrationForm

from .models import User

FORM_MAP = {
    User.Role.DONOR: DonorRegistrationForm,
    User.Role.VOLUNTEER: VolunteerRegistrationForm,
    User.Role.NGO: NGORegistrationForm,
}
