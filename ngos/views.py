from django.contrib.auth.decorators import login_required

from accounts.decorators import role_required
from accounts.models import User

from django.shortcuts import render
from django.utils import timezone

from donations.models import Donation
from .navigation import sidebar


@login_required
@role_required(User.Role.NGO)
def dashboard(request):
    profile = request.user.ngo_profile
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
