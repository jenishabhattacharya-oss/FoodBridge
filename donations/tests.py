from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import User
from donors.models import DonorProfile
from ngos.models import NGOProfile
from volunteers.models import Pickup, VolunteerProfile
from volunteers.services import claim_pickup, mark_collected, mark_delivered

from .models import Donation
from .forms import DonationForm
from .services import (
    confirm_ngo_receipt,
    accept_for_volunteer_delivery,
    create_donation,
    release_ngo_donation,
    takeover_donation,
    submit_donation_for_verification,
)


class DonationWorkflowTests(TestCase):
    def setUp(self):
        self.donor = User.objects.create_user(email="donor@example.com", password="password", first_name="Donor", last_name="One", phone="111", role=User.Role.DONOR)
        DonorProfile.objects.create(user=self.donor, address="MG Road", city="Bengaluru")
        self.volunteer = User.objects.create_user(email="volunteer@example.com", password="password", first_name="Volunteer", last_name="One", phone="222", role=User.Role.VOLUNTEER)
        VolunteerProfile.objects.create(user=self.volunteer, service_area="Bengaluru")
        self.ngo = User.objects.create_user(email="ngo@example.com", password="password", first_name="NGO", last_name="One", phone="333", role=User.Role.NGO)
        NGOProfile.objects.create(user=self.ngo, organization_name="Hope", address="Indiranagar")

    def donation_data(self):
        start = timezone.now() + timedelta(hours=1)
        return {
            "title": "Cooked rice", "description": "Feeds 40 people", "food_type": Donation.FoodType.VEG,
            "food_condition": Donation.FoodCondition.COOKED, "quantity": 40, "unit": Donation.Unit.PLATES,
            "prepared_at": timezone.now(), "storage_notes": "Keep covered", "allergen_notes": "None",
            "pickup_address": "MG Road, Bengaluru", "pickup_window_start": start, "pickup_window_end": start + timedelta(hours=2),
        }

    def test_creation_generates_open_pickup_and_volunteer_progress_syncs_status(self):
        donation = create_donation(donor=self.donor, cleaned_data=self.donation_data())
        self.assertEqual(donation.pickup.status, Pickup.Status.OPEN)
        self.assertEqual(donation.pickup.pickup_city, "Bengaluru")
        accept_for_volunteer_delivery(donation_id=donation.id, ngo=self.ngo)
        claim_pickup(pickup_id=donation.pickup_id, volunteer=self.volunteer)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.Status.VOLUNTEER_CLAIMED)
        mark_collected(pickup_id=donation.pickup_id, volunteer=self.volunteer)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.Status.IN_TRANSIT)
        image = SimpleUploadedFile("proof.gif", b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;", content_type="image/gif")
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            mark_delivered(pickup_id=donation.pickup_id, volunteer=self.volunteer, recipient_name="Hope", recipient_address="Indiranagar", handoff_notes="Received", delivery_photo=image)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.Status.AWAITING_NGO_CONFIRMATION)

    def test_ngo_can_take_over_only_when_no_eligible_volunteer_exists_and_must_upload_proof(self):
        donation = create_donation(donor=self.donor, cleaned_data=self.donation_data())
        with self.assertRaisesMessage(ValidationError, "eligible volunteer"):
            takeover_donation(donation_id=donation.id, ngo=self.ngo)
        self.volunteer.volunteer_profile.is_available = False
        self.volunteer.volunteer_profile.save()
        takeover_donation(donation_id=donation.id, ngo=self.ngo)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.Status.NGO_MANAGED)
        self.assertEqual(donation.pickup.status, Pickup.Status.CANCELLED)
        image = SimpleUploadedFile("receipt.gif", b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;", content_type="image/gif")
        confirm_ngo_receipt(donation_id=donation.id, ngo=self.ngo, receipt_photo=image)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.Status.DELIVERED)

    def _ngo_managed_donation(self):
        donation = create_donation(donor=self.donor, cleaned_data=self.donation_data())
        self.volunteer.volunteer_profile.is_available = False
        self.volunteer.volunteer_profile.save()
        takeover_donation(donation_id=donation.id, ngo=self.ngo)
        return donation

    def test_ngo_reject_returns_unexpired_donation_to_available_pickup_queue(self):
        donation = self._ngo_managed_donation()

        release_ngo_donation(donation_id=donation.id, ngo=self.ngo)

        donation.refresh_from_db()
        donation.pickup.refresh_from_db()
        self.assertIsNone(donation.claimed_by_ngo)
        self.assertEqual(donation.status, Donation.Status.AVAILABLE)
        self.assertEqual(donation.pickup.status, Pickup.Status.OPEN)

    def test_only_accepting_ngo_can_reject_a_managed_donation(self):
        donation = self._ngo_managed_donation()
        other_ngo = User.objects.create_user(email="other-ngo@example.com", password="password", first_name="Other", last_name="NGO", phone="444", role=User.Role.NGO)
        NGOProfile.objects.create(user=other_ngo, organization_name="Other Hope", address="Koramangala")

        with self.assertRaisesMessage(ValidationError, "Only the NGO"):
            release_ngo_donation(donation_id=donation.id, ngo=other_ngo)

    def test_expired_managed_donation_cannot_be_reopened(self):
        donation = self._ngo_managed_donation()
        donation.pickup_window_end = timezone.now() - timedelta(minutes=1)
        donation.save(update_fields=("pickup_window_end", "updated_at"))

        with self.assertRaisesMessage(ValidationError, "pickup window has expired"):
            release_ngo_donation(donation_id=donation.id, ngo=self.ngo)

    def test_managed_donations_page_has_specific_empty_state(self):
        self.client.force_login(self.ngo)

        response = self.client.get("/donations/managed/")

        self.assertContains(response, "No donations accepted yet")


class DonationPhotoVerificationTests(TestCase):
    def setUp(self):
        self.donor = User.objects.create_user(email="photo@example.com", password="password", first_name="Photo", last_name="Donor", phone="555", role=User.Role.DONOR)
        DonorProfile.objects.create(user=self.donor, address="MG Road", city="Bengaluru")

    def _image(self, name):
        return SimpleUploadedFile(name, b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;", content_type="image/gif")

    def _data(self):
        start = timezone.now() + timedelta(hours=1)
        return {"title": "Fresh meals", "description": "Prepared today", "food_type": Donation.FoodType.VEG, "food_condition": Donation.FoodCondition.COOKED, "quantity": 10, "unit": Donation.Unit.PLATES, "prepared_at": timezone.now(), "storage_notes": "", "allergen_notes": "", "pickup_address": "MG Road", "pickup_window_start": start, "pickup_window_end": start + timedelta(hours=1), "food_photo_overview": self._image("overview.gif"), "food_photo_closeup": self._image("closeup.gif"), "food_photo_label": self._image("label.gif")}

    def test_all_three_photos_are_required(self):
        data = self._data()
        data.pop("food_photo_label")
        form = DonationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("food_photo_label", form.errors)

    def test_label_photo_is_optional_for_unpackaged_food(self):
        data = self._data()
        files = {
            "food_photo_overview": data.pop("food_photo_overview"),
            "food_photo_closeup": data.pop("food_photo_closeup"),
        }
        data.pop("food_photo_label")
        data["is_unpackaged"] = "on"

        form = DonationForm(data=data, files=files)

        self.assertTrue(form.is_valid(), form.errors)

    @patch("donations.services.FoodSafetyVerifier.verify")
    def test_approved_screening_creates_pickup(self, verify):
        verify.return_value = {"decision": "approve", "confidence": 90, "summary": "No visible concern.", "risk_flags": []}
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            donation = submit_donation_for_verification(donor=self.donor, cleaned_data=self._data())
        self.assertEqual(donation.verification_status, Donation.VerificationStatus.APPROVED)
        self.assertIsNotNone(donation.pickup_id)

    @patch("donations.services.FoodSafetyVerifier.verify")
    def test_review_result_creates_no_pickup(self, verify):
        verify.return_value = {"decision": "review", "confidence": 20, "summary": "Photos are unclear.", "risk_flags": ["unclear_image"]}
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            donation = submit_donation_for_verification(donor=self.donor, cleaned_data=self._data())
        self.assertEqual(donation.verification_status, Donation.VerificationStatus.HUMAN_REVIEW)
        self.assertIsNone(donation.pickup_id)


class DonationFormPresentationTests(TestCase):
    def setUp(self):
        self.donor = User.objects.create_user(
            email="form@example.com", password="password", first_name="Form", last_name="Donor",
            phone="666", role=User.Role.DONOR,
        )
        DonorProfile.objects.create(user=self.donor, address="MG Road", city="Bengaluru")
        self.client.force_login(self.donor)

    def test_create_form_uses_grouped_sections_and_preserves_all_fields(self):
        response = self.client.get("/donations/new/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Food details")
        self.assertContains(response, "Safety and photos")
        self.assertContains(response, "Pickup details")
        self.assertContains(response, "enctype=\"multipart/form-data\"")
        for field in DonationForm.Meta.fields:
            self.assertContains(response, f'name="{field}"')

    def test_missing_photo_errors_render_beside_upload_cards(self):
        start = timezone.now() + timedelta(hours=1)
        response = self.client.post("/donations/new/", {
            "title": "Fresh meals", "description": "Prepared today", "food_type": Donation.FoodType.VEG,
            "food_condition": Donation.FoodCondition.COOKED, "quantity": 10, "unit": Donation.Unit.PLATES,
            "prepared_at": start.strftime("%Y-%m-%dT%H:%M"), "storage_notes": "", "allergen_notes": "",
            "pickup_address": "MG Road", "pickup_window_start": start.strftime("%Y-%m-%dT%H:%M"),
            "pickup_window_end": (start + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This photo is required for visual food screening.", count=3)
