from django.test import TestCase
from django.urls import reverse

from donors.forms import DonorRegistrationForm
from ngos.forms import NGORegistrationForm
from volunteers.forms import VolunteerRegistrationForm


class RegistrationEntryPointTests(TestCase):
    def test_home_page_role_calls_to_action_link_to_the_matching_registration_form(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, 'href="/register/?role=VOLUNTEER"')
        self.assertContains(response, 'href="/register/?role=NGO"')

    def test_registration_selects_the_requested_role_form(self):
        cases = (
            ("VOLUNTEER", VolunteerRegistrationForm),
            ("NGO", NGORegistrationForm),
        )

        for role, form_class in cases:
            with self.subTest(role=role):
                response = self.client.get(reverse("register"), {"role": role})

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["selected_role"], role)
                self.assertIsInstance(response.context["form"], form_class)

    def test_registration_defaults_to_the_donor_form(self):
        response = self.client.get(reverse("register"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_role"], "DONOR")
        self.assertIsInstance(response.context["form"], DonorRegistrationForm)
