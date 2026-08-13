from io import StringIO
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase, override_settings

from accounts.models import User
from donations.models import Donation
from payments.models import VolunteerPayment, VolunteerPayoutProfile
from volunteers.models import Pickup, VolunteerProfile

class DemoSeedCommandTests(TestCase):
    def test_seed_demo_is_idempotent_and_preserves_non_demo_users(self):
        ordinary_user = User.objects.create_user(
            email="ordinary@example.com", password="password", first_name="Ordinary",
            last_name="User", phone="9000000099", role=User.Role.DONOR,
        )

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            output = StringIO()
            call_command("seed_demo", stdout=output)
            first_count = Donation.objects.filter(donor__email__startswith="demo.").count()
            call_command("seed_demo", stdout=StringIO())

        self.assertIn("FoodBridge demonstration dataset is ready.", output.getvalue())
        self.assertTrue(User.objects.filter(pk=ordinary_user.pk).exists())
        self.assertEqual(Donation.objects.filter(donor__email__startswith="demo.").count(), first_count)
        self.assertEqual(first_count, 9)
        self.assertEqual(User.objects.filter(email__startswith="demo.").count(), 4)

    def test_seed_demo_creates_featured_workflow_states_and_evidence(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root, PAYMENT_ENCRYPTION_KEY="demo-test-key"):
            call_command("seed_demo", stdout=StringIO())

            completed = Donation.objects.get(title="[DEMO] Completed volunteer delivery")
            review = Donation.objects.get(title="[DEMO] Food safety review required")
            managed = Donation.objects.get(title="[DEMO] NGO takeover awaiting receipt")

            self.assertEqual(completed.status, Donation.Status.DELIVERED)
            self.assertEqual(completed.pickup.status, Pickup.Status.DELIVERED)
            self.assertTrue(completed.pickup.delivery_photo.name)
            self.assertEqual(completed.pickup.volunteer_payment.status, VolunteerPayment.Status.PAYOUT_PROCESSED)
            self.assertEqual(review.verification_status, Donation.VerificationStatus.HUMAN_REVIEW)
            self.assertIsNone(review.pickup_id)
            self.assertEqual(managed.status, Donation.Status.NGO_MANAGED)
            self.assertEqual(managed.pickup.status, Pickup.Status.CANCELLED)
            profile = VolunteerProfile.objects.get(user__email="demo.volunteer@foodbridge.local")
            self.assertTrue(profile.location_sharing_consent)
            self.assertIsNotNone(profile.location_updated_at)
            payout_profile = VolunteerPayoutProfile.objects.get(volunteer=profile.user)
            self.assertEqual(payout_profile.upi_id(), "demo.volunteer@upi")
