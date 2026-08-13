from datetime import timedelta
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import User
from donations.models import Donation
from donations.services import accept_for_volunteer_delivery, create_donation
from donors.models import DonorProfile
from ngos.models import NGOProfile
from volunteers.models import VolunteerProfile
from volunteers.services import claim_pickup, mark_collected, mark_delivered

from .models import VolunteerPayment, VolunteerPayoutProfile
from .services import confirm_delivery


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
