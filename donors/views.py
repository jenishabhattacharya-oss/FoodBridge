# Create your views here.
from django.contrib.auth.decorators import login_required

from accounts.decorators import role_required
from accounts.models import User

from django.contrib import messages
from django.shortcuts import redirect, render

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
    dashboard = {
        "welcome": {
            "message": (
                "Create a food listing and FoodBridge will connect it to a pickup volunteer."
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
                "trend": "+12%",
                "subtitle": "Compared to last month",
                "color": "warning",
            },
            {
                "title": "Food Donations",
                "value": donations.count(),
                "icon": "bi-heart-fill",
                "trend": "+3",
                "subtitle": "This month",
                "color": "success",
            },
            {
                "title": "Pending Pickups",
                "value": available,
                "icon": "bi-truck",
                "trend": "Active",
                "subtitle": "Awaiting volunteer assignment",
                "color": "primary",
            },
            {
                "title": "NGOs Helped",
                "value": donations.filter(claimed_by_ngo__isnull=False).count(),
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
