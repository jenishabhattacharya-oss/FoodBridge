from django.urls import reverse

from .models import User


def get_dashboard_url(user):
    dashboard_map = {
        User.Role.DONOR: reverse("donor_dashboard"),
        User.Role.VOLUNTEER: reverse("volunteer_dashboard"),
        User.Role.NGO: reverse("ngo_dashboard"),
    }

    return dashboard_map.get(user.role, reverse("home"))
