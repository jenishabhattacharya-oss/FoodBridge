# Create your views here.
from django.contrib.auth.decorators import login_required

from accounts.decorators import role_required
from accounts.models import User

from django.shortcuts import render


@login_required
@role_required(User.Role.DONOR)
def dashboard(request):
    dashboard = {
        "welcome": {
            "message": (
                "You have donated 18 food packages, helping serve "
                "approximately 246 meals this month."
            ),
            "button": {
                "label": "Donate Again",
                "url": "#",
            },
        },
        "stats": [
            {
                "title": "Meals Served",
                "value": 246,
                "icon": "bi-basket2-fill",
                "trend": "+12%",
                "subtitle": "Compared to last month",
                "color": "warning",
            },
            {
                "title": "Food Donations",
                "value": 18,
                "icon": "bi-heart-fill",
                "trend": "+3",
                "subtitle": "This month",
                "color": "success",
            },
            {
                "title": "Pending Pickups",
                "value": 2,
                "icon": "bi-truck",
                "trend": "Active",
                "subtitle": "Awaiting volunteer assignment",
                "color": "primary",
            },
            {
                "title": "NGOs Helped",
                "value": 7,
                "icon": "bi-building",
                "trend": "+1",
                "subtitle": "New partner this month",
                "color": "info",
            },
        ],
    }

    return render(
        request,
        "donors/dashboard.html",
        {
            "dashboard": dashboard,
        },
    )
