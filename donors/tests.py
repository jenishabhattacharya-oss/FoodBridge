from django.utils import timezone
from django.test import TestCase

from accounts.models import User
from donations.models import Donation

class DonorDashboardTests(TestCase):
    def setUp(self):
        self.donor = User.objects.create_user(
            email="donor@example.com",
            password="test-password",
            first_name="Donor",
            last_name="Example",
            phone="9000000001",
            role=User.Role.DONOR,
        )
        self.ngo = User.objects.create_user(
            email="ngo@example.com",
            password="test-password",
            first_name="NGO",
            last_name="Partner",
            phone="9000000002",
            role=User.Role.NGO,
        )

    def create_donation(self, **overrides):
        now = timezone.now()
        values = {
            "donor": self.donor,
            "title": "Fresh meals",
            "description": "Prepared meals for collection.",
            "food_type": Donation.FoodType.VEG,
            "food_condition": Donation.FoodCondition.COOKED,
            "quantity": 4,
            "unit": Donation.Unit.PLATES,
            "prepared_at": now,
            "pickup_address": "1 Food Street",
            "pickup_window_start": now,
            "pickup_window_end": now + timezone.timedelta(hours=2),
        }
        values.update(overrides)
        return Donation.objects.create(**values)

    def test_stats_use_real_counts_and_distinct_ngo_partners(self):
        self.create_donation(
            title="Delivered meals",
            status=Donation.Status.DELIVERED,
            claimed_by_ngo=self.ngo,
        )
        self.create_donation(
            title="Second delivered meal",
            status=Donation.Status.DELIVERED,
            receiving_ngo=self.ngo,
        )
        self.create_donation(title="Awaiting collection")

        self.client.force_login(self.donor)
        response = self.client.get("/donor/dashboard/")

        self.assertEqual(response.status_code, 200)
        stats = response.context["dashboard"]["stats"]
        self.assertEqual([stat["value"] for stat in stats], [2, 3, 1, 1])
        self.assertEqual(stats[0]["trend"], "0 this month")
        self.assertEqual(stats[1]["trend"], "3 this month")
        self.assertEqual(stats[2]["trend"], "Open")
        self.assertEqual(stats[3]["trend"], "1 this month")
