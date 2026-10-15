from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

import requests
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from donations.models import Donation
from donations.services import accept_for_volunteer_delivery, create_donation
from donors.models import DonorProfile
from ngos.models import NGOProfile
from volunteers.models import VolunteerProfile
from volunteers.services import claim_pickup, mark_collected, mark_delivered

from .models import NGOPaymentConnection, VolunteerPayment, VolunteerPayoutProfile
from .services import (confirm_delivery, create_checkout_order, process_webhook,
                       record_checkout_payment, release_payout, save_oauth_connection,
                       verify_checkout_signature, verify_webhook)


@override_settings(PAYMENT_ENCRYPTION_KEY="payment-test-key")
class VolunteerPaymentTests(TestCase):
    def setUp(self):
        self.donor = User.objects.create_user(email="donor@payment.test", password="password", first_name="Donor", last_name="Test", phone="111", role=User.Role.DONOR)
        DonorProfile.objects.create(user=self.donor, address="MG Road", city="Bengaluru")
        self.ngo = User.objects.create_user(email="ngo@payment.test", password="password", first_name="NGO", last_name="Test", phone="222", role=User.Role.NGO)
        NGOProfile.objects.create(user=self.ngo, organization_name="Hope", address="Indiranagar")
        self.volunteer = User.objects.create_user(email="volunteer@payment.test", password="password", first_name="Volunteer", last_name="Test", phone="333", role=User.Role.VOLUNTEER)
        VolunteerProfile.objects.create(user=self.volunteer, service_area="Bengaluru")

    def test_delivery_confirmation_creates_single_payment_for_assigned_ngo(self):
        start = timezone.now() + timedelta(hours=1)
        donation = create_donation(donor=self.donor, cleaned_data={"title": "Meals", "description": "Meals", "food_type": Donation.FoodType.VEG, "food_condition": Donation.FoodCondition.COOKED, "quantity": 5, "unit": Donation.Unit.PLATES, "prepared_at": timezone.now(), "storage_notes": "", "allergen_notes": "", "pickup_address": "MG Road", "pickup_window_start": start, "pickup_window_end": start + timedelta(hours=1)})
        accept_for_volunteer_delivery(donation_id=donation.id, ngo=self.ngo)
        claim_pickup(pickup_id=donation.pickup_id, volunteer=self.volunteer)
        mark_collected(pickup_id=donation.pickup_id, volunteer=self.volunteer)
        proof = SimpleUploadedFile("proof.gif", b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;", content_type="image/gif")
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            mark_delivered(pickup_id=donation.pickup_id, volunteer=self.volunteer, recipient_name="Hope", recipient_address="Indiranagar", handoff_notes="Received", delivery_photo=proof)
        payment = confirm_delivery(pickup_id=donation.pickup_id, ngo=self.ngo)
        self.assertEqual(payment.amount_paise, 50000)
        self.assertEqual(payment.status, VolunteerPayment.Status.AWAITING_NGO_PAYMENT)
        self.assertEqual(VolunteerPayment.objects.count(), 1)

    def test_payout_profile_encrypts_and_masks_upi(self):
        profile = VolunteerPayoutProfile(volunteer=self.volunteer, destination=VolunteerPayoutProfile.Destination.UPI)
        profile.set_upi_id("volunteer@upi")
        profile.save()
        self.assertNotIn("volunteer@upi", profile.upi_id_encrypted)
        self.assertEqual(profile.masked_destination, "••••@upi")

    def _payment(self):
        start = timezone.now() + timedelta(hours=1)
        donation = create_donation(donor=self.donor, cleaned_data={"title": "Meals", "description": "Meals", "food_type": Donation.FoodType.VEG, "food_condition": Donation.FoodCondition.COOKED, "quantity": 5, "unit": Donation.Unit.PLATES, "prepared_at": timezone.now(), "storage_notes": "", "allergen_notes": "", "pickup_address": "MG Road", "pickup_window_start": start, "pickup_window_end": start + timedelta(hours=1)})
        accept_for_volunteer_delivery(donation_id=donation.id, ngo=self.ngo)
        claim_pickup(pickup_id=donation.pickup_id, volunteer=self.volunteer)
        mark_collected(pickup_id=donation.pickup_id, volunteer=self.volunteer)
        proof = SimpleUploadedFile("proof.gif", b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;", content_type="image/gif")
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            mark_delivered(pickup_id=donation.pickup_id, volunteer=self.volunteer, recipient_name="Hope", recipient_address="Indiranagar", handoff_notes="Received", delivery_photo=proof)
        return confirm_delivery(pickup_id=donation.pickup_id, ngo=self.ngo)

    def _connected_ngo(self):
        connection = NGOPaymentConnection(ngo=self.ngo, razorpay_account_id="acc_test")
        connection.set_access_token("access-token")
        connection.set_refresh_token("refresh-token")
        connection.save()
        return connection

    def test_oauth_connection_encrypts_tokens_and_records_expiry(self):
        before = timezone.now()
        connection = save_oauth_connection(ngo=self.ngo, payload={"razorpay_account_id": "acc_oauth", "access_token": "oauth-access", "refresh_token": "oauth-refresh", "expires_in": 3600})
        self.assertNotIn("oauth-access", connection.access_token_encrypted)
        self.assertNotIn("oauth-refresh", connection.refresh_token_encrypted)
        self.assertEqual(connection.access_token(), "oauth-access")
        self.assertEqual(connection.refresh_token(), "oauth-refresh")
        self.assertTrue(connection.is_active)
        self.assertGreater(connection.expires_at, before + timedelta(minutes=59))

    def test_oauth_connection_rejects_missing_credentials(self):
        with self.assertRaises(ValidationError):
            save_oauth_connection(ngo=self.ngo, payload={"account_id": "acc_test"})

    @override_settings(PAYMENTS_ENABLED=True, RAZORPAY_OAUTH_CLIENT_ID="oauth-client", RAZORPAY_OAUTH_CLIENT_SECRET="oauth-secret", RAZORPAY_OAUTH_REDIRECT_URI="https://shareplate.example/payments/ngo/oauth/callback/")
    def test_oauth_flow_checks_state_before_saving_connection(self):
        profile = self.ngo.ngo_profile
        profile.approval_status = NGOProfile.ApprovalStatus.APPROVED
        profile.save()
        self.client.force_login(self.ngo)
        response = self.client.get(reverse("connect_razorpay"))
        self.assertEqual(response.status_code, 302)
        callback_url = reverse("razorpay_oauth_callback")
        with patch("payments.views.exchange_oauth_code") as exchange:
            bad_response = self.client.get(callback_url, {"state": "wrong", "code": "code"})
            self.assertEqual(bad_response.status_code, 400)
            exchange.assert_not_called()

        response = self.client.get(reverse("connect_razorpay"))
        state = parse_qs(urlparse(response["Location"]).query)["state"][0]
        with patch("payments.views.exchange_oauth_code", return_value={"razorpay_account_id": "acc_callback", "access_token": "callback-token"}) as exchange:
            callback = self.client.get(callback_url, {"state": state, "code": "valid-code"})
        self.assertEqual(callback.status_code, 302)
        exchange.assert_called_once_with(code="valid-code")
        connection = NGOPaymentConnection.objects.get(ngo=self.ngo)
        self.assertEqual(connection.access_token(), "callback-token")

    @override_settings(RAZORPAY_KEY_SECRET="checkout-secret")
    def test_checkout_signature_is_verified(self):
        import hashlib
        import hmac
        signature = hmac.new(b"checkout-secret", b"order_test|pay_test", hashlib.sha256).hexdigest()
        self.assertTrue(verify_checkout_signature(order_id="order_test", payment_id="pay_test", signature=signature))
        self.assertFalse(verify_checkout_signature(order_id="order_test", payment_id="pay_test", signature="bad"))

    @override_settings(RAZORPAY_KEY_SECRET="")
    def test_checkout_signature_requires_configured_secret(self):
        with self.assertRaises(ImproperlyConfigured):
            verify_checkout_signature(order_id="order_test", payment_id="pay_test", signature="bad")

    @override_settings(RAZORPAY_MODE="test", RAZORPAY_KEY_ID="rzp_test_key", RAZORPAY_KEY_SECRET="checkout-secret")
    def test_order_creation_uses_connected_account_token_and_fixed_amount(self):
        payment = self._payment()
        self._connected_ngo()
        response = Mock()
        response.json.return_value = {"id": "order_test"}
        with patch("payments.services.requests.request", return_value=response) as request:
            updated, order = create_checkout_order(payment=payment, ngo=self.ngo)
        self.assertEqual(order["id"], "order_test")
        self.assertEqual(updated.razorpay_order_id, "order_test")
        self.assertEqual(updated.status, VolunteerPayment.Status.PAYMENT_PENDING)
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer access-token")
        self.assertEqual(request.call_args.kwargs["json"]["amount"], 50000)

    @override_settings(RAZORPAY_MODE="test", RAZORPAY_KEY_ID="rzp_live_wrong", RAZORPAY_KEY_SECRET="checkout-secret")
    def test_order_creation_rejects_key_from_wrong_mode(self):
        payment = self._payment()
        self._connected_ngo()
        with self.assertRaises(ImproperlyConfigured):
            create_checkout_order(payment=payment, ngo=self.ngo)

    @override_settings(RAZORPAY_WEBHOOK_SECRET="webhook-secret")
    def test_webhook_signature_accepts_only_matching_body(self):
        import hashlib
        import hmac
        body = b'{"event":"payment.captured"}'
        signature = hmac.new(b"webhook-secret", body, hashlib.sha256).hexdigest()
        self.assertTrue(verify_webhook(body=body, signature=signature))
        self.assertFalse(verify_webhook(body=body, signature="invalid"))

    @override_settings(PAYMENTS_ENABLED=True, RAZORPAY_WEBHOOK_SECRET="webhook-secret")
    def test_invalid_webhook_signature_cannot_change_payment(self):
        payment = self._payment()
        payment.razorpay_order_id = "order_test"
        payment.status = VolunteerPayment.Status.PAYMENT_PENDING
        payment.save()
        body = b'{"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_test","order_id":"order_test"}}}}'
        response = self.client.post(reverse("razorpay_webhook"), body, content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE="invalid")
        self.assertEqual(response.status_code, 400)
        payment.refresh_from_db()
        self.assertEqual(payment.status, VolunteerPayment.Status.PAYMENT_PENDING)

    def test_captured_and_failed_payment_webhooks_drive_payment_state(self):
        payment = self._payment()
        payment.razorpay_order_id = "order_test"
        payment.status = VolunteerPayment.Status.PAYMENT_PENDING
        payment.save()
        process_webhook({"event": "payment.captured", "payload": {"payment": {"entity": {"id": "pay_test", "order_id": "order_test"}}}})
        payment.refresh_from_db()
        self.assertEqual(payment.status, VolunteerPayment.Status.PAYOUT_READY)
        self.assertEqual(payment.razorpay_payment_id, "pay_test")
        process_webhook({"event": "payment.failed", "payload": {"payment": {"entity": {"id": "pay_test", "order_id": "order_test", "error_description": "Declined"}}}})
        payment.refresh_from_db()
        self.assertEqual(payment.status, VolunteerPayment.Status.PAYOUT_READY)
        self.assertEqual(payment.failure_reason, "")

    def test_order_paid_webhook_uses_order_entity_without_payment_entity(self):
        payment = self._payment()
        payment.razorpay_order_id = "order_test"
        payment.status = VolunteerPayment.Status.PAYMENT_PENDING
        payment.save()
        process_webhook({"event": "order.paid", "payload": {"order": {"entity": {"id": "order_test"}}}})
        payment.refresh_from_db()
        self.assertEqual(payment.status, VolunteerPayment.Status.PAYOUT_READY)

    def test_verified_browser_callback_does_not_mark_payment_paid(self):
        payment = self._payment()
        payment.razorpay_order_id = "order_test"
        payment.status = VolunteerPayment.Status.PAYMENT_PENDING
        payment.save()
        updated = record_checkout_payment(payment=payment, ngo=self.ngo, payment_id="pay_test")
        self.assertEqual(updated.razorpay_payment_id, "pay_test")
        self.assertEqual(updated.status, VolunteerPayment.Status.PAYMENT_PENDING)

    @override_settings(RAZORPAYX_ACCOUNT_NUMBER="x_account")
    def test_payout_submission_persists_and_reuses_idempotency_key(self):
        payment = self._payment()
        self._connected_ngo()
        payment.status = VolunteerPayment.Status.PAYOUT_READY
        payment.save()
        profile = VolunteerPayoutProfile(volunteer=self.volunteer, destination=VolunteerPayoutProfile.Destination.UPI)
        profile.set_upi_id("volunteer@upi")
        profile.save()
        def response(payload):
            item = Mock()
            item.json.return_value = payload
            return item
        with patch("payments.services.requests.request", side_effect=[response({"id": "cont_test"}), response({"id": "fa_test"}), response({"id": "pout_test"})]) as request:
            released = release_payout(payment=payment, ngo=self.ngo)
        key = released.payout_idempotency_key
        self.assertTrue(key)
        self.assertEqual(released.razorpay_payout_id, "pout_test")
        self.assertEqual(released.status, VolunteerPayment.Status.PAYOUT_PROCESSING)
        self.assertEqual(request.call_args.kwargs["headers"]["X-Payout-Idempotency"], key)

    @override_settings(RAZORPAYX_ACCOUNT_NUMBER="x_account")
    def test_payout_retry_after_network_error_reuses_committed_key(self):
        payment = self._payment()
        self._connected_ngo()
        payment.status = VolunteerPayment.Status.PAYOUT_READY
        payment.save()
        profile = VolunteerPayoutProfile(volunteer=self.volunteer, destination=VolunteerPayoutProfile.Destination.UPI)
        profile.set_upi_id("volunteer@upi")
        profile.save()
        def response(payload):
            item = Mock()
            item.json.return_value = payload
            return item
        with patch("payments.services.requests.request", side_effect=[response({"id": "cont_1"}), response({"id": "fa_1"}), requests.Timeout("timeout")]):
            with self.assertRaises(requests.Timeout):
                release_payout(payment=payment, ngo=self.ngo)
        payment.refresh_from_db()
        key = payment.payout_idempotency_key
        self.assertTrue(key)
        with patch("payments.services.requests.request", side_effect=[response({"id": "cont_2"}), response({"id": "fa_2"}), response({"id": "pout_retry"})]) as request:
            released = release_payout(payment=payment, ngo=self.ngo)
        self.assertEqual(request.call_args.kwargs["headers"]["X-Payout-Idempotency"], key)
        self.assertEqual(released.razorpay_payout_id, "pout_retry")

    def test_payout_webhook_failure_and_duplicate_delivery_are_safe(self):
        payment = self._payment()
        payment.razorpay_payout_id = "pout_test"
        payment.status = VolunteerPayment.Status.PAYOUT_PROCESSING
        payment.save()
        failed = {"event": "payout.reversed", "payload": {"payout": {"entity": {"id": "pout_test", "failure_reason": "Bank rejected"}}}}
        process_webhook(failed)
        process_webhook(failed)
        payment.refresh_from_db()
        self.assertEqual(payment.status, VolunteerPayment.Status.PAYOUT_FAILED)
        self.assertEqual(payment.failure_reason, "Bank rejected")

    def test_payout_processed_is_terminal_for_late_failure_events(self):
        payment = self._payment()
        payment.razorpay_payout_id = "pout_test"
        payment.status = VolunteerPayment.Status.PAYOUT_PROCESSING
        payment.save()
        process_webhook({"event": "payout.processed", "payload": {"payout": {"entity": {"id": "pout_test"}}}})
        process_webhook({"event": "payout.failed", "payload": {"payout": {"entity": {"id": "pout_test", "failure_reason": "late event"}}}})
        payment.refresh_from_db()
        self.assertEqual(payment.status, VolunteerPayment.Status.PAYOUT_PROCESSED)
