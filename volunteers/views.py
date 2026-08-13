from datetime import date, timedelta
from math import asin, cos, radians, sin, sqrt

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from decimal import Decimal, InvalidOperation

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
    items = [
        ("Dashboard", "bi-speedometer2", "volunteer_dashboard"),
        ("Available Pickups", "bi-box-seam", "available_pickups"),
        ("Assigned Pickups", "bi-truck", "assigned_pickups"),
        ("Pickup History", "bi-clock-history", "pickup_history"),
        ("My Profile", "bi-person-gear", "volunteer_profile"),
    ]
    if settings.PAYMENTS_ENABLED:
        items.append(("Payout details", "bi-credit-card", "volunteer_payout_profile"))
    return [
        {"label": label, "icon": icon, "url": reverse(url_name), "active": label == active_label}
        for label, icon, url_name in items
    ]


def _profile(user):
    profile, _ = VolunteerProfile.objects.get_or_create(user=user)
    return profile


def _available_queryset(request, default_city=""):
    pickups = Pickup.objects.filter(
        status=Pickup.Status.OPEN,
        donation__status="NGO_ACCEPTED",
        donation__receiving_ngo__isnull=False,
        donation__pickup_window_end__gt=timezone.now(),
    ).select_related("donation__receiving_ngo")
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


def _distance_km(latitude, longitude, pickup):
    if latitude is None or longitude is None or pickup.pickup_latitude is None or pickup.pickup_longitude is None:
        return None
    lat1, lon1, lat2, lon2 = map(radians, (float(latitude), float(longitude), float(pickup.pickup_latitude), float(pickup.pickup_longitude)))
    return round(6371 * 2 * asin(sqrt(sin((lat2-lat1)/2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2-lon1)/2) ** 2)), 1)


def _distance_metres(latitude, longitude, other_latitude, other_longitude):
    lat1, lon1, lat2, lon2 = map(radians, (float(latitude), float(longitude), float(other_latitude), float(other_longitude)))
    return 6371000 * 2 * asin(sqrt(sin((lat2-lat1)/2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2-lon1)/2) ** 2))


def _visible_pickup_or_404(request, pickup_id):
    pickup = get_object_or_404(Pickup, pk=pickup_id)
    if pickup.status != Pickup.Status.OPEN and pickup.assigned_volunteer_id != request.user.id:
        raise Http404("Pickup not found.")
    return pickup


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
def dashboard(request):
    profile = _profile(request.user)
    available, _, _ = _available_queryset(request, profile.service_area)
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
        "profile": profile,
        "sidebar_items": _sidebar("Dashboard"),
        "page_title": "Volunteer Dashboard",
    })


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
def available_pickups(request):
    profile = _profile(request.user)
    pickups, city, pickup_date = _available_queryset(request, profile.service_area)
    fresh_location = profile.location_updated_at and timezone.now() - profile.location_updated_at <= timedelta(minutes=5)
    pickups = list(pickups)
    for pickup in pickups:
        pickup.distance_km = _distance_km(profile.current_latitude, profile.current_longitude, pickup) if fresh_location else None
    if fresh_location:
        pickups.sort(key=lambda pickup: pickup.distance_km is None)
    return render(request, "volunteers/available_pickups.html", {
        "pickups": pickups,
        "city": city,
        "pickup_date": pickup_date,
        "sidebar_items": _sidebar("Available Pickups"),
        "page_title": "Available Pickups",
        "has_fresh_location": fresh_location,
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
        "destination_name": pickup.destination_place_label or "Receiving NGO",
    })


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
@require_POST
def accept_pickup(request, pickup_id):
    try:
        if settings.PAYMENTS_ENABLED and not hasattr(request.user, "payout_profile"):
            raise PickupUnavailable("Add your payout details before claiming a paid pickup.")
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


@login_required(login_url="login")
@role_required(User.Role.VOLUNTEER)
@require_POST
def update_location(request):
    profile = _profile(request.user)
    if not profile.is_available or not profile.location_sharing_consent:
        return JsonResponse({"detail": "Location sharing is not enabled."}, status=409)
    try:
        latitude = Decimal(request.POST["latitude"])
        longitude = Decimal(request.POST["longitude"])
    except (KeyError, InvalidOperation):
        return JsonResponse({"detail": "Valid coordinates are required."}, status=400)
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return JsonResponse({"detail": "Coordinates are outside valid bounds."}, status=400)
    now = timezone.now()
    seconds_since_update = (now - profile.location_updated_at).total_seconds() if profile.location_updated_at else None
    moved_metres = _distance_metres(latitude, longitude, profile.current_latitude, profile.current_longitude) if profile.current_latitude is not None else 0
    if seconds_since_update is not None and seconds_since_update < 30 and moved_metres < 50:
        return JsonResponse({"detail": "Location received recently."}, status=429)
    profile.current_latitude = latitude
    profile.current_longitude = longitude
    profile.location_updated_at = now
    profile.save(update_fields=("current_latitude", "current_longitude", "location_updated_at"))
    return JsonResponse({"status": "updated", "updated_at": now.isoformat()})
