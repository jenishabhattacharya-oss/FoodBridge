import hashlib
import hmac
import json
import secrets
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import transaction
from django.utils import timezone

from donations.models import Donation
from volunteers.models import Pickup

from .models import NGOPaymentConnection, VolunteerPayment, VolunteerPayoutProfile


RAZORPAY_API = "https://api.razorpay.com/v1"
RAZORPAY_AUTH = "https://auth.razorpay.com"


def _require(value, name):
    if not value:
        raise ImproperlyConfigured(f"{name} is not configured.")
    return value


def oauth_authorize_url(state):
    return f"{RAZORPAY_AUTH}/authorize?{urlencode({
        'client_id': _require(settings.RAZORPAY_OAUTH_CLIENT_ID, 'RAZORPAY_OAUTH_CLIENT_ID'),
        'redirect_uri': _require(settings.RAZORPAY_OAUTH_REDIRECT_URI, 'RAZORPAY_OAUTH_REDIRECT_URI'),
        'response_type': 'code', 'state': state,
    })}"


def exchange_oauth_code(*, code):
    response = requests.post(f"{RAZORPAY_AUTH}/token", data={
        "grant_type": "authorization_code", "code": code,
        "client_id": _require(settings.RAZORPAY_OAUTH_CLIENT_ID, "RAZORPAY_OAUTH_CLIENT_ID"),
        "client_secret": _require(settings.RAZORPAY_OAUTH_CLIENT_SECRET, "RAZORPAY_OAUTH_CLIENT_SECRET"),
        "redirect_uri": _require(settings.RAZORPAY_OAUTH_REDIRECT_URI, "RAZORPAY_OAUTH_REDIRECT_URI"),
    }, timeout=10)
    response.raise_for_status()
    return response.json()


def save_oauth_connection(*, ngo, payload):
    account_id = payload.get("razorpay_account_id") or payload.get("account_id")
    if not account_id or not payload.get("access_token"):
        raise ValidationError("Razorpay did not return an account ID and access token.")
    connection, _ = NGOPaymentConnection.objects.get_or_create(ngo=ngo, defaults={"razorpay_account_id": account_id})
    connection.razorpay_account_id = account_id
    connection.set_access_token(payload["access_token"])
    connection.set_refresh_token(payload.get("refresh_token", ""))
    expires_in = payload.get("expires_in")
    connection.expires_at = timezone.now() + timedelta(seconds=int(expires_in)) if expires_in else None
    connection.is_active = True
    connection.save()
    return connection


def _api(connection, method, path, *, data=None, headers=None):
    response = requests.request(method, f"{RAZORPAY_API}{path}", json=data, headers={
        "Authorization": f"Bearer {connection.access_token()}",
        **(headers or {}),
    }, timeout=10)
    response.raise_for_status()
    return response.json()


@transaction.atomic
def confirm_delivery(*, pickup_id, ngo):
    pickup = Pickup.objects.select_for_update().select_related("donation", "assigned_volunteer").get(pk=pickup_id)
    donation = pickup.donation
    if donation.receiving_ngo_id != ngo.id or pickup.status != Pickup.Status.DELIVERED:
        raise ValidationError("This delivery is not awaiting confirmation by your NGO.")
    if donation.status != Donation.Status.AWAITING_NGO_CONFIRMATION:
        raise ValidationError("This delivery has already been confirmed.")
    if not pickup.assigned_volunteer_id:
        raise ValidationError("This pickup has no assigned volunteer.")
    payment, created = VolunteerPayment.objects.get_or_create(
        pickup=pickup, defaults={"ngo": ngo, "volunteer": pickup.assigned_volunteer, "amount_paise": settings.VOLUNTEER_DELIVERY_FEE_PAISE},
    )
    if not created and payment.ngo_id != ngo.id:
        raise ValidationError("This payment belongs to another NGO.")
    payment.status = VolunteerPayment.Status.AWAITING_NGO_PAYMENT
    payment.ngo_confirmed_at = timezone.now()
    payment.failure_reason = ""
    payment.save()
    donation.status = Donation.Status.DELIVERED
    donation.save(update_fields=("status", "updated_at"))
    return payment


@transaction.atomic
def create_checkout_order(*, payment, ngo):
    payment = VolunteerPayment.objects.select_for_update().select_related("ngo__payment_connection").get(pk=payment.pk)
    if payment.ngo_id != ngo.id or payment.status not in (VolunteerPayment.Status.AWAITING_NGO_PAYMENT, VolunteerPayment.Status.PAYMENT_FAILED):
        raise ValidationError("This payment cannot be started.")
    try:
        connection = ngo.payment_connection
    except NGOPaymentConnection.DoesNotExist:
        raise ValidationError("Connect your Razorpay account before paying a volunteer.")
    if not connection.is_active:
        raise ValidationError("Your Razorpay connection is inactive.")
    order = _api(connection, "POST", "/orders", data={
        "amount": payment.amount_paise, "currency": "INR", "receipt": f"foodbridge-{payment.pk}", "notes": {"payment_id": str(payment.pk), "pickup_id": str(payment.pickup_id)},
    })
    payment.razorpay_order_id = order["id"]
    payment.status = VolunteerPayment.Status.PAYMENT_PENDING
    payment.failure_reason = ""
    payment.save(update_fields=("razorpay_order_id", "status", "failure_reason", "updated_at"))
    return payment, order


@transaction.atomic
def record_checkout_payment(*, payment, ngo, payment_id):
    payment = VolunteerPayment.objects.select_for_update().get(pk=payment.pk)
    if payment.ngo_id != ngo.id or payment.status != VolunteerPayment.Status.PAYMENT_PENDING:
        raise ValidationError("This payment is not awaiting Checkout confirmation.")
    # Browser callbacks are only a convenience; the verified webhook remains authoritative.
    payment.razorpay_payment_id = payment_id
    payment.save(update_fields=("razorpay_payment_id", "updated_at"))
    return payment


def verify_checkout_signature(*, order_id, payment_id, signature):
    secret = _require(settings.RAZORPAY_KEY_SECRET, "RAZORPAY_KEY_SECRET")
    expected = hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def _payout_destination(profile):
    if profile.destination == VolunteerPayoutProfile.Destination.UPI:
        return {"account_type": "vpa", "vpa": {"address": profile.upi_id()} }
    return {"account_type": "bank_account", "bank_account": {"name": profile.account_holder(), "ifsc": profile.ifsc(), "account_number": profile.account_number()}}


@transaction.atomic
def release_payout(*, payment, ngo):
    payment = VolunteerPayment.objects.select_for_update().select_related("volunteer", "ngo__payment_connection").get(pk=payment.pk)
    if payment.ngo_id != ngo.id or payment.status not in (VolunteerPayment.Status.PAYOUT_READY, VolunteerPayment.Status.PAYOUT_FAILED):
        raise ValidationError("This payout is not ready to release.")
    try:
        connection = ngo.payment_connection
        profile = payment.volunteer.payout_profile
    except (NGOPaymentConnection.DoesNotExist, VolunteerPayoutProfile.DoesNotExist):
        raise ValidationError("A Razorpay connection and volunteer payout details are required.")
    contact = _api(connection, "POST", "/contacts", data={"name": payment.volunteer.get_full_name(), "email": payment.volunteer.email, "contact": payment.volunteer.phone, "type": "employee", "reference_id": f"foodbridge-volunteer-{payment.volunteer_id}"})
    fund_account = _api(connection, "POST", "/fund_accounts", data={"contact_id": contact["id"], **_payout_destination(profile)})
    key = payment.payout_idempotency_key or secrets.token_hex(24)
    payout = _api(connection, "POST", "/payouts", data={"account_number": _require(settings.RAZORPAYX_ACCOUNT_NUMBER, "RAZORPAYX_ACCOUNT_NUMBER"), "fund_account_id": fund_account["id"], "amount": payment.amount_paise, "currency": "INR", "mode": "UPI" if profile.destination == profile.Destination.UPI else "IMPS", "purpose": "salary", "queue_if_low_balance": True, "reference_id": f"foodbridge-{payment.pk}"}, headers={"X-Payout-Idempotency": key})
    payment.razorpay_contact_id = contact["id"]
    payment.razorpay_fund_account_id = fund_account["id"]
    payment.razorpay_payout_id = payout["id"]
    payment.payout_idempotency_key = key
    payment.status = VolunteerPayment.Status.PAYOUT_PROCESSING
    payment.payout_released_at = timezone.now()
    payment.failure_reason = ""
    payment.save()
    return payment


def verify_webhook(*, body, signature):
    secret = _require(settings.RAZORPAY_WEBHOOK_SECRET, "RAZORPAY_WEBHOOK_SECRET")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


@transaction.atomic
def process_webhook(event):
    payload = event.get("payload", {})
    payment_entity = payload.get("payment", {}).get("entity", {})
    payout_entity = payload.get("payout", {}).get("entity", {})
    event_name = event.get("event")
    if payment_entity.get("id"):
        payment = VolunteerPayment.objects.select_for_update().filter(razorpay_order_id=payment_entity.get("order_id")).first()
        if not payment: return
        if event_name in ("payment.captured", "order.paid") and payment.status in (VolunteerPayment.Status.PAYMENT_PENDING, VolunteerPayment.Status.PAYMENT_FAILED):
            payment.razorpay_payment_id = payment_entity["id"]
            payment.status = VolunteerPayment.Status.PAYOUT_READY
            payment.paid_at = timezone.now()
            payment.failure_reason = ""
        elif event_name == "payment.failed" and payment.status == VolunteerPayment.Status.PAYMENT_PENDING:
            payment.status = VolunteerPayment.Status.PAYMENT_FAILED
            payment.failure_reason = payment_entity.get("error_description", "Payment failed")[:255]
        payment.save()
    elif payout_entity.get("id"):
        payment = VolunteerPayment.objects.select_for_update().filter(razorpay_payout_id=payout_entity["id"]).first()
        if not payment: return
        if event_name == "payout.processed" and payment.status == VolunteerPayment.Status.PAYOUT_PROCESSING:
            payment.status = VolunteerPayment.Status.PAYOUT_PROCESSED
        elif event_name in ("payout.failed", "payout.reversed") and payment.status == VolunteerPayment.Status.PAYOUT_PROCESSING:
            payment.status = VolunteerPayment.Status.PAYOUT_FAILED
            payment.failure_reason = payout_entity.get("status_details", {}).get("description", "Payout failed")[:255]
        payment.save()
