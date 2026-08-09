from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from donors.navigation import sidebar as donor_sidebar
from donors.models import DonorProfile
from ngos.navigation import sidebar as ngo_sidebar

from .forms import DonationForm, NGOReceiptForm
from .models import Donation
from .services import (
    cancel_donation,
    confirm_ngo_receipt,
    create_donation,
    eligible_volunteers,
    release_ngo_donation,
    takeover_donation,
    update_donation,
)


def _active_donations():
    return Donation.objects.filter(status=Donation.Status.AVAILABLE, pickup_window_end__gt=timezone.now())


@login_required(login_url="login")
@role_required(User.Role.DONOR)
def create(request):
    profile, _ = DonorProfile.objects.get_or_create(
        user=request.user,
        defaults={"address": "Please update your pickup address", "city": ""},
    )
    if not profile.city:
        messages.info(request, "Add your city to your donor profile before creating a listing.")
        return redirect("donor_profile")
    form = DonationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        donation = create_donation(donor=request.user, cleaned_data=form.cleaned_data)
        messages.success(request, "Donation listed and sent to the volunteer pickup queue.")
        return redirect("donation_detail", donation_id=donation.id)
    return render(request, "donations/form.html", {
        "form": form,
        "page_title": "Donate surplus food",
        "base_template": "dashboards/base_dashboard.html",
        "sidebar_items": donor_sidebar("Donate food"),
    })


@login_required(login_url="login")
@role_required(User.Role.DONOR)
def mine(request):
    donations = Donation.objects.filter(donor=request.user).select_related("pickup", "claimed_by_ngo")
    return render(request, "donations/list.html", {
        "donations": donations,
        "page_title": "My donations",
        "mine": True,
        "base_template": "dashboards/base_dashboard.html",
        "sidebar_items": donor_sidebar("My donations"),
    })


@login_required(login_url="login")
@role_required(User.Role.NGO)
def ngo_list(request):
    donations = _active_donations().select_related("donor__donor_profile", "pickup")
    return render(request, "donations/list.html", {
        "donations": donations,
        "page_title": "Available food",
        "mine": False,
        "base_template": "dashboards/base_dashboard.html",
        "sidebar_items": ngo_sidebar("Available food"),
    })


@login_required(login_url="login")
@role_required(User.Role.NGO)
def ngo_managed(request):
    donations = Donation.objects.filter(claimed_by_ngo=request.user).select_related("donor", "pickup")
    return render(request, "donations/ngo_managed.html", {
        "donations": donations,
        "page_title": "Managed donations",
        "mine": False,
        "base_template": "dashboards/base_dashboard.html",
        "sidebar_items": ngo_sidebar("Managed donations"),
    })


@login_required(login_url="login")
def detail(request, donation_id):
    donation = get_object_or_404(Donation.objects.select_related("donor", "pickup", "claimed_by_ngo", "donor__donor_profile"), pk=donation_id)
    if request.user.role == User.Role.DONOR and donation.donor_id != request.user.id:
        raise Http404("Donation not found.")
    if request.user.role == User.Role.NGO and (donation.effective_status != Donation.Status.AVAILABLE and donation.claimed_by_ngo_id != request.user.id):
        raise Http404("Donation not found.")
    if request.user.role not in (User.Role.DONOR, User.Role.NGO):
        raise Http404("Donation not found.")
    can_takeover = (
        request.user.role == User.Role.NGO and donation.can_be_changed
        and donation.pickup.status == donation.pickup.Status.OPEN
        and not eligible_volunteers(donation.donor.donor_profile.city).exists()
    )
    is_managed_by_current_ngo = donation.claimed_by_ngo_id == request.user.id
    receipt_form = NGOReceiptForm(instance=donation) if is_managed_by_current_ngo and donation.status == Donation.Status.NGO_MANAGED else None
    can_reject = (
        is_managed_by_current_ngo
        and donation.status == Donation.Status.NGO_MANAGED
        and donation.pickup_window_end > timezone.now()
    )
    context = {
        "donation": donation,
        "can_takeover": can_takeover,
        "can_reject": can_reject,
        "receipt_form": receipt_form,
    }
    if request.user.role == User.Role.DONOR:
        context.update({
            "base_template": "dashboards/base_dashboard.html",
            "sidebar_items": donor_sidebar("My donations"),
            "page_title": "Donation details",
        })
    elif request.user.role == User.Role.NGO:
        context.update({
            "base_template": "dashboards/base_dashboard.html",
            "sidebar_items": ngo_sidebar("Managed donations" if donation.claimed_by_ngo_id == request.user.id else "Available food"),
            "page_title": "Food listing details",
        })
    return render(request, "donations/detail.html", context)


@login_required(login_url="login")
@role_required(User.Role.DONOR)
def edit(request, donation_id):
    donation = get_object_or_404(Donation, pk=donation_id, donor=request.user)
    if not donation.can_be_changed:
        messages.error(request, "This donation can no longer be edited.")
        return redirect("donation_detail", donation_id=donation.id)
    form = DonationForm(request.POST or None, instance=donation)
    if request.method == "POST" and form.is_valid():
        try:
            donation = update_donation(donation_id=donation.id, donor=request.user, cleaned_data=form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Donation and pickup details updated.")
            return redirect("donation_detail", donation_id=donation.id)
    return render(request, "donations/form.html", {
        "form": form,
        "page_title": "Edit donation",
        "base_template": "dashboards/base_dashboard.html",
        "sidebar_items": donor_sidebar("My donations"),
    })


@login_required(login_url="login")
@role_required(User.Role.DONOR)
@require_POST
def cancel(request, donation_id):
    try:
        cancel_donation(donation_id=donation_id, donor=request.user)
    except Donation.DoesNotExist:
        raise Http404("Donation not found.")
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, "Donation cancelled and removed from the volunteer queue.")
    return redirect("my_donations")


@login_required(login_url="login")
@role_required(User.Role.NGO)
@require_POST
def takeover(request, donation_id):
    try:
        donation = takeover_donation(donation_id=donation_id, ngo=request.user)
    except Donation.DoesNotExist:
        raise Http404("Donation not found.")
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, "Your organization is now responsible for this donation.")
        return redirect("donation_detail", donation_id=donation.id)
    return redirect("ngo_donations")


@login_required(login_url="login")
@role_required(User.Role.NGO)
@require_POST
def reject_ngo_donation(request, donation_id):
    try:
        release_ngo_donation(donation_id=donation_id, ngo=request.user)
    except Donation.DoesNotExist:
        raise Http404("Donation not found.")
    except ValidationError as error:
        messages.error(request, error.messages[0])
        return redirect("donation_detail", donation_id=donation_id)

    messages.success(request, "Donation rejected and returned to the available food queue.")
    return redirect("ngo_managed_donations")


@login_required(login_url="login")
@role_required(User.Role.NGO)
@require_POST
def confirm_receipt(request, donation_id):
    donation = get_object_or_404(Donation, pk=donation_id, claimed_by_ngo=request.user)
    form = NGOReceiptForm(request.POST, request.FILES, instance=donation)
    if form.is_valid():
        try:
            confirm_ngo_receipt(donation_id=donation.id, ngo=request.user, receipt_photo=form.cleaned_data["receipt_photo"])
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Receipt confirmed. Thank you for completing the donation.")
            return redirect("donation_detail", donation_id=donation.id)
    return render(request, "donations/detail.html", {
        "donation": donation,
        "receipt_form": form,
        "can_takeover": False,
        "can_reject": False,
        "base_template": "dashboards/base_dashboard.html",
        "sidebar_items": ngo_sidebar("Managed donations"),
        "page_title": "Food listing details",
    })
