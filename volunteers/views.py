from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User

from .forms import DeliveryForm, VolunteerProfileForm
from .models import Pickup, VolunteerProfile
from .services import (
    ActivePickupLimitReached,
    InvalidPickupTransition,
    PickupAccessDenied,
    PickupUnavailable,
    claim_pickup,
    mark_collected,
    mark_delivered,
)


def _sidebar(active_label):
    items = (
        ("Dashboard", "bi-speedometer2", "volunteer_dashboard"),
        ("Available Pickups", "bi-box-seam", "available_pickups"),
        ("Assigned Pickups", "bi-truck", "assigned_pickups"),
        ("Pickup History", "bi-clock-history", "pickup_history"),
        ("My Profile", "bi-person-gear", "volunteer_profile"),
    )
    return [
        {"label": label, "icon": icon, "url": reverse(url_name), "active": label == active_label}
        for label, icon, url_name in items
    ]


def _profile(user):
    profile, _ = VolunteerProfile.objects.get_or_create(user=user)
    return profile


def _available_queryset(request, default_city=""):
    pickups = Pickup.objects.filter(status=Pickup.Status.OPEN)
    city = request.GET.get("city", default_city).strip()
    if city:
        pickups = pickups.filter(pickup_city__iexact=city)

    pickup_date = request.GET.get("date", "").strip()
    if pickup_date:
        try:
            pickups = pickups.filter(pickup_window_start__date=date.fromisoformat(pickup_date))
        except ValueError:
            pickup_date = ""
    return pickups, city, pickup_date


def _visible_pickup_or_404(request, pickup_id):
    pickup = get_object_or_404(Pickup, pk=pickup_id)
    if pickup.status != Pickup.Status.OPEN and pickup.assigned_volunteer_id != request.user.id:
        raise Http404("Pickup not found.")
    return pickup


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
def dashboard(request):
    profile = _profile(request.user)
    available = Pickup.objects.filter(status=Pickup.Status.OPEN)
    if profile.service_area:
        available = available.filter(pickup_city__iexact=profile.service_area)
    active = Pickup.objects.filter(
        assigned_volunteer=request.user,
        status__in=(Pickup.Status.CLAIMED, Pickup.Status.COLLECTED),
    )
    delivered = Pickup.objects.filter(assigned_volunteer=request.user, status=Pickup.Status.DELIVERED)
    dashboard_data = {
        "welcome": {
            "message": "Manage your active pickup and help food reach people who need it.",
            "button": {"label": "View Available Pickups", "url": reverse("available_pickups")},
        },
        "stats": [
            {"title": "Available Pickups", "value": available.count(), "icon": "bi-box-seam", "trend": "Open", "subtitle": "In your service area" if profile.service_area else "Waiting for volunteers", "color": "primary"},
            {"title": "Active Pickups", "value": active.count(), "icon": "bi-truck", "trend": "Active" if active else "None", "subtitle": "Claimed or collected", "color": "warning"},
            {"title": "Delivered", "value": delivered.count(), "icon": "bi-check2-circle", "trend": "Complete", "subtitle": "Your completed pickups", "color": "success"},
        ],
    }
    return render(request, "volunteers/dashboard.html", {
        "dashboard": dashboard_data,
        "available_pickups": available[:5],
        "assigned_pickups": active,
        "sidebar_items": _sidebar("Dashboard"),
        "page_title": "Volunteer Dashboard",
    })


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
def available_pickups(request):
    profile = _profile(request.user)
    pickups, city, pickup_date = _available_queryset(request, profile.service_area)
    return render(request, "volunteers/available_pickups.html", {
        "pickups": pickups,
        "city": city,
        "pickup_date": pickup_date,
        "sidebar_items": _sidebar("Available Pickups"),
        "page_title": "Available Pickups",
    })


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
def pickup_details(request, pickup_id):
    pickup = _visible_pickup_or_404(request, pickup_id)
    return render(request, "volunteers/pickup_details.html", {
        "pickup": pickup,
        "delivery_form": DeliveryForm(instance=pickup),
        "sidebar_items": _sidebar("Assigned Pickups" if pickup.assigned_volunteer_id else "Available Pickups"),
        "page_title": "Pickup Details",
    })


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
@require_POST
def accept_pickup(request, pickup_id):
    try:
        claim_pickup(pickup_id=pickup_id, volunteer=request.user)
    except Pickup.DoesNotExist:
        raise Http404("Pickup not found.")
    except (PickupUnavailable, ActivePickupLimitReached) as error:
        messages.error(request, str(error))
        return redirect("available_pickups")
    messages.success(request, "Pickup claimed successfully.")
    return redirect("assigned_pickups")


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
@require_POST
def collect_pickup(request, pickup_id):
    try:
        mark_collected(pickup_id=pickup_id, volunteer=request.user)
    except Pickup.DoesNotExist:
        raise Http404("Pickup not found.")
    except (PickupAccessDenied, InvalidPickupTransition) as error:
        messages.error(request, str(error))
        return redirect("assigned_pickups")
    else:
        messages.success(request, "Pickup marked as collected. Confirm delivery after handoff.")
    return redirect("pickup_details", pickup_id=pickup_id)


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
@require_POST
def deliver_pickup(request, pickup_id):
    pickup = _visible_pickup_or_404(request, pickup_id)
    form = DeliveryForm(request.POST, request.FILES, instance=pickup)
    if form.is_valid():
        try:
            mark_delivered(
                pickup_id=pickup_id,
                volunteer=request.user,
                recipient_name=form.cleaned_data["recipient_name"],
                recipient_address=form.cleaned_data["recipient_address"],
                handoff_notes=form.cleaned_data["handoff_notes"],
                delivery_photo=form.cleaned_data["delivery_photo"],
            )
        except (PickupAccessDenied, InvalidPickupTransition) as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Delivery confirmed. Thank you for completing the pickup.")
            return redirect("pickup_history")
    return render(request, "volunteers/pickup_details.html", {
        "pickup": pickup,
        "delivery_form": form,
        "sidebar_items": _sidebar("Assigned Pickups"),
        "page_title": "Pickup Details",
    })


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
def assigned_pickups(request):
    pickups = Pickup.objects.filter(
        assigned_volunteer=request.user,
        status__in=(Pickup.Status.CLAIMED, Pickup.Status.COLLECTED),
    )
    return render(request, "volunteers/assigned_pickups.html", {
        "pickups": pickups,
        "sidebar_items": _sidebar("Assigned Pickups"),
        "page_title": "Assigned Pickups",
    })


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
def pickup_history(request):
    pickups = Pickup.objects.filter(assigned_volunteer=request.user, status=Pickup.Status.DELIVERED)
    return render(request, "volunteers/pickup_history.html", {
        "pickups": pickups,
        "sidebar_items": _sidebar("Pickup History"),
        "page_title": "Pickup History",
    })


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
def volunteer_profile(request):
    profile = _profile(request.user)
    if request.method == "POST":
        form = VolunteerProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your volunteer profile has been updated.")
            return redirect("volunteer_profile")
    else:
        form = VolunteerProfileForm(instance=profile, user=request.user)
    return render(request, "volunteers/profile.html", {
        "form": form,
        "sidebar_items": _sidebar("My Profile"),
        "page_title": "My Volunteer Profile",
    })
