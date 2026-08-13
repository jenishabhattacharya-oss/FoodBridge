import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


def _cipher():
    key = settings.PAYMENT_ENCRYPTION_KEY
    if not key:
        raise ImproperlyConfigured("PAYMENT_ENCRYPTION_KEY must be configured before storing payment details.")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()))


class NGOPaymentConnection(models.Model):
    ngo = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payment_connection")
    razorpay_account_id = models.CharField(max_length=100, unique=True)
    access_token_encrypted = models.TextField()
    refresh_token_encrypted = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_access_token(self, token):
        self.access_token_encrypted = _cipher().encrypt(token.encode()).decode()

    def access_token(self):
        return _cipher().decrypt(self.access_token_encrypted.encode()).decode()

    def set_refresh_token(self, token):
        self.refresh_token_encrypted = _cipher().encrypt(token.encode()).decode() if token else ""

    def refresh_token(self):
        return _cipher().decrypt(self.refresh_token_encrypted.encode()).decode() if self.refresh_token_encrypted else ""


class VolunteerPayoutProfile(models.Model):
    class Destination(models.TextChoices):
        UPI = "UPI", "UPI"
        BANK = "BANK", "Bank account"

    volunteer = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payout_profile")
    destination = models.CharField(max_length=10, choices=Destination.choices)
    upi_id_encrypted = models.TextField(blank=True)
    account_holder_encrypted = models.TextField(blank=True)
    account_number_encrypted = models.TextField(blank=True)
    ifsc_encrypted = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def _set(self, field, value):
        setattr(self, field, _cipher().encrypt(value.encode()).decode() if value else "")

    def _get(self, field):
        value = getattr(self, field)
        return _cipher().decrypt(value.encode()).decode() if value else ""

    def set_upi_id(self, value): self._set("upi_id_encrypted", value)
    def upi_id(self): return self._get("upi_id_encrypted")
    def set_account_holder(self, value): self._set("account_holder_encrypted", value)
    def account_holder(self): return self._get("account_holder_encrypted")
    def set_account_number(self, value): self._set("account_number_encrypted", value)
    def account_number(self): return self._get("account_number_encrypted")
    def set_ifsc(self, value): self._set("ifsc_encrypted", value)
    def ifsc(self): return self._get("ifsc_encrypted")

    @property
    def masked_destination(self):
        if self.destination == self.Destination.UPI:
            value = self.upi_id()
            return f"••••{value[-4:]}" if value else "Not configured"
        value = self.account_number()
        return f"••••{value[-4:]}" if value else "Not configured"


class VolunteerPayment(models.Model):
    class Status(models.TextChoices):
        AWAITING_NGO_CONFIRMATION = "AWAITING_NGO_CONFIRMATION", "Awaiting NGO confirmation"
        AWAITING_NGO_PAYMENT = "AWAITING_NGO_PAYMENT", "Awaiting NGO payment"
        PAYMENT_PENDING = "PAYMENT_PENDING", "Payment pending"
        PAYMENT_CAPTURED = "PAYMENT_CAPTURED", "Payment captured"
        PAYMENT_FAILED = "PAYMENT_FAILED", "Payment failed"
        PAYOUT_READY = "PAYOUT_READY", "Payout ready"
        PAYOUT_PROCESSING = "PAYOUT_PROCESSING", "Payout processing"
        PAYOUT_PROCESSED = "PAYOUT_PROCESSED", "Payout processed"
        PAYOUT_FAILED = "PAYOUT_FAILED", "Payout failed"

    pickup = models.OneToOneField("volunteers.Pickup", on_delete=models.CASCADE, related_name="volunteer_payment")
    ngo = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="volunteer_payments")
    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="delivery_payments")
    amount_paise = models.PositiveIntegerField(default=settings.VOLUNTEER_DELIVERY_FEE_PAISE)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.AWAITING_NGO_CONFIRMATION)
    razorpay_order_id = models.CharField(max_length=100, blank=True, unique=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, unique=True, null=True)
    razorpay_payout_id = models.CharField(max_length=100, blank=True, unique=True, null=True)
    razorpay_contact_id = models.CharField(max_length=100, blank=True)
    razorpay_fund_account_id = models.CharField(max_length=100, blank=True)
    payout_idempotency_key = models.CharField(max_length=64, blank=True, unique=True)
    ngo_confirmed_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    payout_released_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
