from django.contrib.auth.decorators import login_required

from accounts.decorators import role_required
from accounts.models import User

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from donations.models import Donation
from .navigation import sidebar
from .forms import NGOProfileForm


@login_required
@role_required(User.Role.NGO)
def dashboard(request):
    profile = request.user.ngo_profile
    if not profile.is_approved:
        return render(request, "ngos/dashboard.html", {
            "profile": profile,
            "pending_approval": True,
            "sidebar_items": sidebar("Dashboard"),
            "page_title": "NGO Dashboard",
        })
    available = Donation.objects.filter(
        status=Donation.Status.AVAILABLE,
        pickup_window_end__gt=timezone.now(),
    ).select_related("donor", "donor__donor_profile")
    managed = Donation.objects.filter(claimed_by_ngo=request.user)
    delivered = managed.filter(status=Donation.Status.DELIVERED).count()
    return render(request, "ngos/dashboard.html", {
        "profile": profile,
        "available_donations": available[:5],
        "managed_donations": managed[:4],
        "stats": (
            {"label": "Available now", "value": available.count(), "icon": "bi-basket2-fill", "note": "Ready for collection"},
            {"label": "Under your care", "value": managed.exclude(status=Donation.Status.DELIVERED).count(), "icon": "bi-box-seam", "note": "Awaiting completion"},
            {"label": "Delivered", "value": delivered, "icon": "bi-check2-circle", "note": "Completed handoffs"},
        ),
        "sidebar_items": sidebar("Dashboard"),
        "page_title": "NGO Dashboard",
    })


@login_required
@role_required(User.Role.NGO)
def profile(request):
    profile = request.user.ngo_profile
    form = NGOProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your organization location has been updated.")
        return redirect("ngo_profile")
    return render(request, "ngos/profile.html", {
        "form": form, "profile": profile, "sidebar_items": sidebar("Location settings"), "page_title": "Organization location",
    })
