from datetime import timedelta
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import Pickup, VolunteerProfile
from .services import ActivePickupLimitReached, create_pickup, claim_pickup, mark_collected


class VolunteerPickupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="volunteer@example.com",
            password="test-password",
            first_name="Volunteer",
            last_name="User",
            phone="1234567890",
            role=User.Role.VOLUNTEER,
        )
        self.profile = VolunteerProfile.objects.create(user=self.user, service_area="Bengaluru")
        self.client.force_login(self.user)

    def create_pickup(self, **overrides):
        start = timezone.now() + timedelta(hours=1)
        data = {
            "donor_name": "Green Cafe",
            "donor_phone": "+919876543210",
            "pickup_address": "MG Road",
            "pickup_city": "Bengaluru",
            "food_description": "Cooked meals",
            "quantity": "40 meals",
            "pickup_window_start": start,
            "pickup_window_end": start + timedelta(hours=1),
            "instructions": "Use rear entrance.",
        }
        data.update(overrides)
        return create_pickup(**data)

    def test_service_creates_a_persistent_open_pickup(self):
        pickup = self.create_pickup()

        self.assertEqual(pickup.status, Pickup.Status.OPEN)
        self.assertIsNone(pickup.assigned_volunteer)
        self.assertTrue(Pickup.objects.filter(pk=pickup.pk).exists())

    def test_pickup_window_and_delivery_evidence_are_validated(self):
        start = timezone.now()
        pickup = Pickup(
            donor_name="Cafe",
            donor_phone="123",
            pickup_address="Address",
            pickup_city="Bengaluru",
            food_description="Meals",
            quantity="10",
            pickup_window_start=start,
            pickup_window_end=start,
        )
        with self.assertRaises(ValidationError):
            pickup.full_clean()

        pickup = self.create_pickup()
        pickup.assigned_volunteer = self.user
        pickup.status = Pickup.Status.DELIVERED
        with self.assertRaises(ValidationError):
            pickup.full_clean()

    def test_claiming_persists_assignment_and_enforces_one_active_pickup(self):
        first = self.create_pickup()
        second = self.create_pickup(donor_name="Pizza Hut")

        claim_pickup(pickup_id=first.id, volunteer=self.user)
        first.refresh_from_db()
        self.assertEqual(first.status, Pickup.Status.CLAIMED)
        self.assertEqual(first.assigned_volunteer, self.user)

        with self.assertRaises(ActivePickupLimitReached):
            claim_pickup(pickup_id=second.id, volunteer=self.user)
        second.refresh_from_db()
        self.assertEqual(second.status, Pickup.Status.OPEN)

    def test_unavailable_volunteer_cannot_claim(self):
        self.profile.is_available = False
        self.profile.save()
        pickup = self.create_pickup()

        response = self.client.post(reverse("accept_pickup", args=[pickup.id]))

        self.assertRedirects(response, reverse("available_pickups"))
        pickup.refresh_from_db()
        self.assertEqual(pickup.status, Pickup.Status.OPEN)

    def test_available_pickups_default_to_profile_city_and_support_date_filter(self):
        today = self.create_pickup()
        other_city = self.create_pickup(donor_name="Delhi Cafe", pickup_city="Delhi")
        tomorrow = self.create_pickup(
            donor_name="Tomorrow Cafe",
            pickup_window_start=timezone.now() + timedelta(days=1),
            pickup_window_end=timezone.now() + timedelta(days=1, hours=1),
        )

        response = self.client.get(reverse("available_pickups"))
        self.assertContains(response, today.donor_name)
        response = self.client.get(reverse("available_pickups"), {"city": "Bengaluru", "date": today.pickup_window_start.date().isoformat()})
        self.assertContains(response, today.donor_name)
        self.assertNotContains(response, other_city.donor_name)
        self.assertNotContains(response, tomorrow.donor_name)

    def test_only_assignee_can_collect_pickup(self):
        pickup = self.create_pickup()
        claim_pickup(pickup_id=pickup.id, volunteer=self.user)
        other = User.objects.create_user(
            email="other@example.com", password="test-password", first_name="Other", last_name="Volunteer", phone="1234567891", role=User.Role.VOLUNTEER
        )
        VolunteerProfile.objects.create(user=other)
        self.client.force_login(other)

        response = self.client.post(reverse("collect_pickup", args=[pickup.id]))

        self.assertRedirects(response, reverse("assigned_pickups"))
        pickup.refresh_from_db()
        self.assertEqual(pickup.status, Pickup.Status.CLAIMED)

    def test_non_assignee_cannot_view_claimed_pickup(self):
        pickup = self.create_pickup()
        claim_pickup(pickup_id=pickup.id, volunteer=self.user)
        other = User.objects.create_user(
            email="other@example.com", password="test-password", first_name="Other", last_name="Volunteer", phone="1234567891", role=User.Role.VOLUNTEER
        )
        VolunteerProfile.objects.create(user=other)
        self.client.force_login(other)

        self.assertEqual(self.client.get(reverse("pickup_details", args=[pickup.id])).status_code, 404)

    def test_delivery_requires_photo_and_moves_pickup_to_history(self):
        pickup = self.create_pickup()
        claim_pickup(pickup_id=pickup.id, volunteer=self.user)
        mark_collected(pickup_id=pickup.id, volunteer=self.user)

        without_photo = self.client.post(reverse("deliver_pickup", args=[pickup.id]), {
            "recipient_name": "Hope Foundation",
            "recipient_address": "Indiranagar",
            "handoff_notes": "Received by manager.",
        })
        self.assertContains(without_photo, "This field is required to confirm delivery.")

        image = SimpleUploadedFile(
            "proof.gif",
            b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(reverse("deliver_pickup", args=[pickup.id]), {
                "recipient_name": "Hope Foundation",
                "recipient_address": "Indiranagar",
                "handoff_notes": "Received by manager.",
                "delivery_photo": image,
            })

        self.assertRedirects(response, reverse("pickup_history"))
        pickup.refresh_from_db()
        self.assertEqual(pickup.status, Pickup.Status.DELIVERED)
        self.assertTrue(pickup.delivery_photo.name)
        history = self.client.get(reverse("pickup_history"))
        self.assertContains(history, "Hope Foundation")

    def test_profile_update_changes_availability_and_contact_details(self):
        response = self.client.post(reverse("volunteer_profile"), {
            "first_name": "Updated",
            "last_name": "Volunteer",
            "phone": "9999999999",
            "service_area": "Mysuru",
            "transport_mode": VolunteerProfile.TransportMode.BICYCLE,
        })

        self.assertRedirects(response, reverse("volunteer_profile"))
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.profile.service_area, "Mysuru")
        self.assertFalse(self.profile.is_available)

    def test_accepting_pickup_requires_post_and_non_volunteers_are_redirected(self):
        pickup = self.create_pickup()
        self.assertEqual(self.client.get(reverse("accept_pickup", args=[pickup.id])).status_code, 405)

        donor = User.objects.create_user(
            email="donor@example.com", password="test-password", first_name="Donor", last_name="User", phone="1234567892", role=User.Role.DONOR
        )
        self.client.force_login(donor)
        self.assertRedirects(self.client.get(reverse("available_pickups")), reverse("home"))
