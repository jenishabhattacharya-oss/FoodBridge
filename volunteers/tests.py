from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class VolunteerPickupViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="volunteer@example.com",
            password="test-password",
            first_name="Volunteer",
            last_name="User",
            phone="1234567890",
            role=User.Role.VOLUNTEER,
        )
        self.client.force_login(self.user)

    def test_pickup_details_returns_404_for_an_unknown_pickup(self):
        response = self.client.get(reverse("pickup_details", args=[999]))

        self.assertEqual(response.status_code, 404)

    def test_accepting_a_pickup_requires_post(self):
        url = reverse("accept_pickup", args=[1])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)

    def test_anonymous_user_is_redirected_before_request_method_is_checked(self):
        self.client.logout()

        response = self.client.get(reverse("accept_pickup", args=[1]))

        self.assertRedirects(response, f"{reverse('login')}?next=/volunteer/pickups/1/accept/")

    def test_accepting_a_pickup_moves_it_to_assigned_pickups(self):
        response = self.client.post(reverse("accept_pickup", args=[1]))

        self.assertRedirects(response, reverse("assigned_pickups"))
        available = self.client.get(reverse("available_pickups"))
        assigned = self.client.get(reverse("assigned_pickups"))
        self.assertNotContains(available, "Green Cafe")
        self.assertContains(assigned, "Green Cafe")

    def test_non_volunteer_cannot_access_pickups(self):
        donor = User.objects.create_user(
            email="donor@example.com",
            password="test-password",
            first_name="Donor",
            last_name="User",
            phone="1234567891",
            role=User.Role.DONOR,
        )
        self.client.force_login(donor)

        response = self.client.get(reverse("available_pickups"))

        self.assertRedirects(response, reverse("home"))
