# Create your views here.
from django.contrib.auth.decorators import login_required

from accounts.decorators import role_required
from accounts.models import User

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from donations.models import Donation
from .forms import DonorProfileForm
from .models import DonorProfile
from .navigation import sidebar


@login_required
@role_required(User.Role.DONOR)
def dashboard(request):
    donations = Donation.objects.filter(donor=request.user).select_related("claimed_by_ngo")
    available = donations.filter(status=Donation.Status.AVAILABLE).count()
    completed = donations.filter(status=Donation.Status.DELIVERED).count()
    month_start = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    donations_this_month = donations.filter(created_at__gte=month_start)
    completed_this_month = donations.filter(
        status=Donation.Status.DELIVERED,
        pickup__delivered_at__gte=month_start,
    ).count()

    # A donor can make multiple donations to one NGO. Count partner
    # organizations, not donation records, so this card remains truthful.
    ngo_ids = set(donations.exclude(claimed_by_ngo__isnull=True).values_list("claimed_by_ngo_id", flat=True))
    ngo_ids.update(donations.exclude(receiving_ngo__isnull=True).values_list("receiving_ngo_id", flat=True))
    monthly_ngo_ids = set(donations_this_month.exclude(claimed_by_ngo__isnull=True).values_list("claimed_by_ngo_id", flat=True))
    monthly_ngo_ids.update(donations_this_month.exclude(receiving_ngo__isnull=True).values_list("receiving_ngo_id", flat=True))

    dashboard = {
        "welcome": {
            "message": (
                "Create a food listing and SharePlate will connect it to a pickup volunteer."
            ),
            "button": {
                "label": "Donate Again",
                "url": "/donations/new/",
            },
        },
        "stats": [
            {
                "title": "Completed Donations",
                "value": completed,
                "icon": "bi-basket2-fill",
                "trend": f"{completed_this_month} this month",
                "trend_tone": "neutral",
                "subtitle": "Delivered successfully",
                "color": "warning",
            },
            {
                "title": "Food Donations",
                "value": donations.count(),
                "icon": "bi-heart-fill",
                "trend": f"{donations_this_month.count()} this month",
                "trend_tone": "neutral",
                "subtitle": "All listings to date",
                "color": "success",
            },
            {
                "title": "Pending Pickups",
                "value": available,
                "icon": "bi-truck",
                "trend": "Open",
                "trend_tone": "active",
                "subtitle": "Awaiting volunteer assignment",
                "color": "primary",
            },
            {
                "title": "NGOs Helped",
                "value": len(ngo_ids),
                "icon": "bi-building",
                "trend": f"{len(monthly_ngo_ids)} this month",
                "trend_tone": "neutral",
                "subtitle": "Partner organizations reached",
                "color": "info",
            },
        ],
    }

    return render(
        request,
        "donors/dashboard.html",
        {
            "dashboard": dashboard,
            "recent_donations": donations[:5],
            "sidebar_items": sidebar("Dashboard"),
            "page_title": "Donor Dashboard",
        },
    )


@login_required
@role_required(User.Role.DONOR)
def profile(request):
    profile, _ = DonorProfile.objects.get_or_create(user=request.user, defaults={"address": ""})
    if request.method == "POST":
        form = DonorProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your donor profile has been updated.")
            return redirect("donor_profile")
    else:
        form = DonorProfileForm(instance=profile, user=request.user)
    return render(request, "donors/profile.html", {
        "form": form,
        "sidebar_items": sidebar("My profile"),
        "page_title": "My Donor Profile",
    })
