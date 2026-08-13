import json
import secrets
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.decorators import approved_ngo_required, role_required
from accounts.models import User
from ngos.navigation import sidebar as ngo_sidebar

from .forms import VolunteerPayoutProfileForm
from .models import VolunteerPayment, VolunteerPayoutProfile
from .services import (confirm_delivery, create_checkout_order, exchange_oauth_code,
                       oauth_authorize_url, process_webhook, record_checkout_payment,
                       release_payout, save_oauth_connection, verify_checkout_signature, verify_webhook)


def payments_enabled(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not settings.PAYMENTS_ENABLED:
            messages.info(request, "Payments are disabled for this closed demo.")
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return wrapper


@login_required
@role_required(User.Role.NGO)
@approved_ngo_required
@payments_enabled
def connect_razorpay(request):
    state = secrets.token_urlsafe(32)
    request.session["razorpay_oauth_state"] = state
    try:
        return redirect(oauth_authorize_url(state))
    except ImproperlyConfigured as error:
        messages.error(request, str(error))
        return redirect("ngo_dashboard")


@login_required
@role_required(User.Role.NGO)
@approved_ngo_required
@payments_enabled
def oauth_callback(request):
    if request.GET.get("state") != request.session.pop("razorpay_oauth_state", None):
        return HttpResponseBadRequest("Invalid Razorpay OAuth state.")
    if not request.GET.get("code"):
        messages.error(request, "Razorpay connection was not completed.")
        return redirect("ngo_dashboard")
    try:
        save_oauth_connection(ngo=request.user, payload=exchange_oauth_code(code=request.GET["code"]))
    except Exception as error:
        messages.error(request, f"Could not connect Razorpay: {error}")
    else:
        messages.success(request, "Razorpay and RazorpayX are connected.")
    return redirect("ngo_dashboard")


@login_required
@role_required(User.Role.VOLUNTEER)
@payments_enabled
def payout_profile(request):
    profile = getattr(request.user, "payout_profile", None)
    if request.method == "POST":
        form = VolunteerPayoutProfileForm(request.POST)
        if form.is_valid():
            profile = profile or VolunteerPayoutProfile(volunteer=request.user)
            profile.destination = form.cleaned_data["destination"]
            profile.set_upi_id(form.cleaned_data.get("upi_id", ""))
            profile.set_account_holder(form.cleaned_data.get("account_holder", ""))
            profile.set_account_number(form.cleaned_data.get("account_number", ""))
            profile.set_ifsc(form.cleaned_data.get("ifsc", ""))
            profile.save()
            messages.success(request, "Payout details saved securely.")
            return redirect("volunteer_payout_profile")
    else:
        initial = {"destination": profile.destination} if profile else None
        form = VolunteerPayoutProfileForm(initial=initial)
    return render(request, "payments/payout_profile.html", {"form": form, "profile": profile})


@login_required
@role_required(User.Role.NGO)
@approved_ngo_required
@payments_enabled
@require_POST
def confirm_volunteer_delivery(request, pickup_id):
    try:
        payment = confirm_delivery(pickup_id=pickup_id, ngo=request.user)
        messages.success(request, "Delivery confirmed. You can now pay the volunteer.")
        return redirect("volunteer_payment_detail", payment_id=payment.id)
    except (ValidationError, Exception) as error:
        messages.error(request, str(error))
        return redirect("ngo_donations")


@login_required
@role_required(User.Role.NGO)
@approved_ngo_required
@payments_enabled
def volunteer_payment_detail(request, payment_id):
    payment = get_object_or_404(VolunteerPayment.objects.select_related("pickup", "volunteer"), pk=payment_id, ngo=request.user)
    return render(request, "payments/payment_detail.html", {"payment": payment, "razorpay_key_id": settings.RAZORPAY_KEY_ID, "sidebar_items": ngo_sidebar("Managed donations"), "page_title": "Volunteer payment"})


@login_required
@role_required(User.Role.NGO)
@approved_ngo_required
@payments_enabled
@require_POST
def create_payment_order(request, payment_id):
    payment = get_object_or_404(VolunteerPayment, pk=payment_id, ngo=request.user)
    try:
        payment, order = create_checkout_order(payment=payment, ngo=request.user)
    except (ValidationError, ImproperlyConfigured, Exception) as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse({"order_id": order["id"], "amount": payment.amount_paise, "currency": "INR", "payment_id": payment.id})


@login_required
@role_required(User.Role.NGO)
@approved_ngo_required
@payments_enabled
@require_POST
def verify_payment_callback(request, payment_id):
    payment = get_object_or_404(VolunteerPayment, pk=payment_id, ngo=request.user)
    payment_reference = request.POST.get("razorpay_payment_id", "")
    if not verify_checkout_signature(order_id=payment.razorpay_order_id, payment_id=payment_reference, signature=request.POST.get("razorpay_signature", "")):
        return JsonResponse({"error": "Invalid Razorpay payment signature."}, status=400)
    try:
        record_checkout_payment(payment=payment, ngo=request.user, payment_id=payment_reference)
    except ValidationError as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse({"ok": True, "message": "Payment submitted. Waiting for Razorpay confirmation."})


@login_required
@role_required(User.Role.NGO)
@approved_ngo_required
@payments_enabled
@require_POST
def release_volunteer_payout(request, payment_id):
    payment = get_object_or_404(VolunteerPayment, pk=payment_id, ngo=request.user)
    try:
        release_payout(payment=payment, ngo=request.user)
    except (ValidationError, ImproperlyConfigured, Exception) as error:
        messages.error(request, f"Could not release payout: {error}")
    else:
        messages.success(request, "Payout submitted to RazorpayX.")
    return redirect("volunteer_payment_detail", payment_id=payment.id)


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    if not settings.PAYMENTS_ENABLED:
        return HttpResponseBadRequest("Payments are disabled.")
    if not verify_webhook(body=request.body, signature=request.headers.get("X-Razorpay-Signature")):
        return HttpResponseBadRequest("Invalid webhook signature.")
    try:
        process_webhook(json.loads(request.body.decode()))
    except (ValueError, KeyError):
        return HttpResponseBadRequest("Invalid webhook payload.")
    return JsonResponse({"ok": True})
