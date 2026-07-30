from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User


# These are temporary demonstration listings until food donations are modelled.
# Keeping them in one place makes every volunteer screen show the same pickup.
PICKUPS = {
    1: {
        "id": 1,
        "donor": "Green Cafe",
        "food": "Cooked Meals",
        "quantity": "40 Meals",
        "address": "MG Road, Bengaluru",
        "window": "5:00 PM - 6:00 PM",
        "distance": "1.8 km",
        "contact": "+91 9876543210",
        "notes": "Please collect from the rear entrance. Ask for the restaurant manager.",
    },
    2: {
        "id": 2,
        "donor": "Pizza Hut",
        "food": "Bakery Items",
        "quantity": "25 Meals",
        "address": "Brigade Road, Bengaluru",
        "window": "7:00 PM - 8:00 PM",
        "distance": "2.5 km",
        "contact": "+91 9876543211",
        "notes": "Please ask for the shift manager at the front counter.",
    },
    3: {
        "id": 3,
        "donor": "Hotel Paradise",
        "food": "Rice & Curry",
        "quantity": "70 Meals",
        "address": "Indiranagar, Bengaluru",
        "window": "7:30 PM - 8:30 PM",
        "distance": "3.1 km",
        "contact": "+91 9876543212",
        "notes": "Bring insulated containers if they are available.",
    },
}


def _sidebar(active_label):
    items = (
        ("Dashboard", "bi-speedometer2", "volunteer_dashboard"),
        ("Available Pickups", "bi-box-seam", "available_pickups"),
        ("Assigned Pickups", "bi-truck", "assigned_pickups"),
        ("Pickup History", "bi-clock-history", "pickup_history"),
    )
    return [
        {
            "label": label,
            "icon": icon,
            "url": reverse(url_name),
            "active": label == active_label,
        }
        for label, icon, url_name in items
    ]


def _accepted_pickup_ids(request):
    return set(request.session.get("accepted_pickup_ids", []))


def _available_pickups(request):
    accepted_ids = _accepted_pickup_ids(request)
    return [pickup for pickup_id, pickup in PICKUPS.items() if pickup_id not in accepted_ids]


def _assigned_pickups(request):
    return [
        {**PICKUPS[pickup_id], "status": "Ready for Pickup"}
        for pickup_id in _accepted_pickup_ids(request)
        if pickup_id in PICKUPS
    ]


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
def dashboard(request):
    available_pickups = _available_pickups(request)
    assigned_pickups = _assigned_pickups(request)
    dashboard_data = {
        "welcome": {
            "message": "Thank you for volunteering! Browse available food donations and make a difference today.",
            "button": {
                "label": "View Available Pickups",
                "url": reverse("available_pickups"),
            },
        },
        "stats": [
            {
                "title": "Available Pickups",
                "value": len(available_pickups),
                "icon": "bi-box-seam",
                "trend": "Open",
                "subtitle": "Waiting for volunteers",
                "color": "primary",
            },
            {
                "title": "Assigned Pickups",
                "value": len(assigned_pickups),
                "icon": "bi-truck",
                "trend": "Active" if assigned_pickups else "None",
                "subtitle": "Currently assigned to you",
                "color": "warning",
            },
        ],
    }
    return render(
        request,
        "volunteers/dashboard.html",
        {
            "dashboard": dashboard_data,
            "available_pickups": available_pickups,
            "assigned_pickups": assigned_pickups,
            "sidebar_items": _sidebar("Dashboard"),
        },
    )


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
def available_pickups(request):
    return render(
        request,
        "volunteers/available_pickups.html",
        {"pickups": _available_pickups(request), "sidebar_items": _sidebar("Available Pickups")},
    )


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
def pickup_details(request, pickup_id):
    pickup = PICKUPS.get(pickup_id)
    if pickup is None:
        raise Http404("Pickup not found.")

    return render(
        request,
        "volunteers/pickup_details.html",
        {
            "pickup": pickup,
            "pickup_is_assigned": pickup_id in _accepted_pickup_ids(request),
            "sidebar_items": _sidebar("Available Pickups"),
        },
    )


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
@require_POST
def accept_pickup(request, pickup_id):
    if pickup_id not in PICKUPS:
        raise Http404("Pickup not found.")

    accepted_ids = _accepted_pickup_ids(request)
    if pickup_id in accepted_ids:
        messages.info(request, "This pickup is already assigned to you.")
    else:
        accepted_ids.add(pickup_id)
        request.session["accepted_pickup_ids"] = sorted(accepted_ids)
        messages.success(request, "Pickup accepted successfully.")

    return redirect("assigned_pickups")


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
def assigned_pickups(request):
    return render(
        request,
        "volunteers/assigned_pickups.html",
        {"pickups": _assigned_pickups(request), "sidebar_items": _sidebar("Assigned Pickups")},
    )


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
def pickup_history(request):
    return render(
        request,
        "volunteers/pickup_history.html",
        {"pickups": [], "sidebar_items": _sidebar("Pickup History")},
    )
