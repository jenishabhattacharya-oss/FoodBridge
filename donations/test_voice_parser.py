import json
from datetime import timedelta
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import Donation
from .voice_parser import (
    REQUIRED_FIELDS,
    DonationVoiceParser,
    VoiceParseError,
    VoiceParserUnavailable,
    VoiceProviderError,
    normalize_voice_fields,
)


def local_format(value):
    return timezone.localtime(value).strftime("%Y-%m-%dT%H:%M")


def gemini_response(payload):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"candidates": [{"content": {"parts": [{"text": payload}]}}]}
    return response


class NormalizeVoiceFieldsTests(SimpleTestCase):
    def setUp(self):
        self.now = timezone.now().replace(second=0, microsecond=0)

    def test_valid_fields_are_normalized_for_the_form(self):
        prepared = self.now - timedelta(hours=1)
        start = self.now + timedelta(hours=1)
        end = self.now + timedelta(hours=3)
        result = normalize_voice_fields({
            "title": "  Veg biryani  ", "description": "Veg biryani left from a wedding.",
            "food_type": "veg", "food_condition": "Cooked", "quantity": "20", "unit": "plates",
            "prepared_at": prepared.isoformat(), "pickup_address": "MG Road, Bengaluru",
            "pickup_window_start": start.isoformat(), "pickup_window_end": end.isoformat(),
            "is_unpackaged": True, "allergen_notes": None,
        }, now=self.now)
        fields = result["fields"]
        self.assertEqual(fields["title"], "Veg biryani")
        self.assertEqual(fields["food_type"], Donation.FoodType.VEG)
        self.assertEqual(fields["food_condition"], Donation.FoodCondition.COOKED)
        self.assertEqual(fields["unit"], Donation.Unit.PLATES)
        self.assertEqual(fields["quantity"], 20)
        self.assertEqual(fields["prepared_at"], local_format(prepared))
        self.assertEqual(fields["pickup_window_end"], local_format(end))
        self.assertTrue(fields["is_unpackaged"])
        self.assertNotIn("allergen_notes", fields)
        self.assertEqual(result["missing_required"], [])

    def test_choice_labels_and_spoken_variants_are_accepted(self):
        result = normalize_voice_fields({"food_type": "Non-vegetarian", "unit": "kg", "food_condition": "packaged"}, now=self.now)
        self.assertEqual(result["fields"]["food_type"], Donation.FoodType.NON_VEG)
        self.assertEqual(result["fields"]["unit"], Donation.Unit.KG)
        self.assertEqual(result["fields"]["food_condition"], Donation.FoodCondition.PACKAGED)

    def test_invalid_values_are_dropped_and_reported_missing(self):
        result = normalize_voice_fields({"food_type": "SEAFOOD", "unit": "litres", "quantity": "twenty", "title": "   "}, now=self.now)
        for name in ("food_type", "unit", "quantity", "title"):
            self.assertNotIn(name, result["fields"])
            self.assertIn(name, result["missing_required"])

    def test_quantity_bounds(self):
        for value in (0, -3, True, 10**9):
            self.assertNotIn("quantity", normalize_voice_fields({"quantity": value}, now=self.now)["fields"])

    def test_pickup_end_before_start_is_dropped(self):
        result = normalize_voice_fields({
            "pickup_window_start": (self.now + timedelta(hours=3)).isoformat(),
            "pickup_window_end": (self.now + timedelta(hours=1)).isoformat(),
        }, now=self.now)
        self.assertNotIn("pickup_window_end", result["fields"])
        self.assertIn("pickup_window_end", result["missing_required"])
        self.assertIn("pickup_window_start", result["uncertain"])

    def test_future_preparation_time_is_dropped(self):
        result = normalize_voice_fields({"prepared_at": (self.now + timedelta(hours=5)).isoformat()}, now=self.now)
        self.assertNotIn("prepared_at", result["fields"])

    def test_model_uncertain_list_is_limited_to_filled_fields(self):
        result = normalize_voice_fields({"title": "Rice", "uncertain": ["title", "unit", "bogus"]}, now=self.now)
        self.assertEqual(result["uncertain"], ["title"])

    def test_non_dict_input_returns_everything_missing(self):
        result = normalize_voice_fields(["unexpected"], now=self.now)
        self.assertEqual(result["fields"], {})
        self.assertEqual(result["missing_required"], list(REQUIRED_FIELDS))


class DonationVoiceParserTests(SimpleTestCase):
    @override_settings(GEMINI_API_KEY="")
    def test_missing_api_key_raises_unavailable(self):
        with self.assertRaises(VoiceParserUnavailable):
            DonationVoiceParser().parse("20 plates of rice")

    @override_settings(GEMINI_API_KEY="test-key")
    def test_empty_and_too_long_transcripts_are_rejected(self):
        for transcript in ("", "   ", "x" * 2001):
            with self.assertRaises(VoiceParseError):
                DonationVoiceParser().parse(transcript)

    @override_settings(GEMINI_API_KEY="test-key")
    def test_successful_parse_sends_key_in_header(self):
        payload = json.dumps({"title": "Rice", "quantity": 5, "unit": "KG"})
        with patch("donations.voice_parser.requests.post", return_value=gemini_response(payload)) as post:
            result = DonationVoiceParser().parse("5 kg of rice")
        self.assertEqual(result["fields"], {"title": "Rice", "quantity": 5, "unit": "KG"})
        self.assertEqual(post.call_args.kwargs["headers"]["x-goog-api-key"], "test-key")
        self.assertNotIn("key=", post.call_args.args[0])

    @override_settings(GEMINI_API_KEY="test-key")
    def test_provider_failures_raise_provider_error(self):
        with patch("donations.voice_parser.requests.post", side_effect=requests.Timeout):
            with self.assertRaises(VoiceProviderError):
                DonationVoiceParser().parse("5 kg of rice")
        with patch("donations.voice_parser.requests.post", return_value=gemini_response("not json")):
            with self.assertRaises(VoiceProviderError):
                DonationVoiceParser().parse("5 kg of rice")


class VoiceParseViewTests(TestCase):
    def setUp(self):
        self.url = reverse("donation_voice_parse")
        self.donor = User.objects.create_user(email="voice-donor@example.com", password="password", first_name="Voice", last_name="Donor", phone="444", role=User.Role.DONOR)
        self.volunteer = User.objects.create_user(email="voice-volunteer@example.com", password="password", first_name="Voice", last_name="Volunteer", phone="555", role=User.Role.VOLUNTEER)

    def post(self, payload):
        return self.client.post(self.url, data=payload if isinstance(payload, str) else json.dumps(payload), content_type="application/json")

    def test_donor_receives_parsed_fields(self):
        self.client.force_login(self.donor)
        parsed = {"fields": {"title": "Rice"}, "missing_required": ["description"], "uncertain": []}
        with patch("donations.voice_views.DonationVoiceParser.parse", return_value=parsed) as parse:
            response = self.post({"transcript": "Some rice"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), parsed)
        parse.assert_called_once_with("Some rice")

    def test_requires_login(self):
        self.assertEqual(self.post({"transcript": "Rice"}).status_code, 302)

    def test_requires_donor_role(self):
        self.client.force_login(self.volunteer)
        self.assertNotEqual(self.post({"transcript": "Rice"}).status_code, 200)

    def test_get_is_not_allowed(self):
        self.client.force_login(self.donor)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_invalid_payloads_return_400(self):
        self.client.force_login(self.donor)
        self.assertEqual(self.post("{").status_code, 400)
        self.assertEqual(self.post({"transcript": 42}).status_code, 400)
        self.assertEqual(self.post(["Rice"]).status_code, 400)

    @override_settings(GEMINI_API_KEY="")
    def test_unconfigured_provider_returns_503(self):
        self.client.force_login(self.donor)
        self.assertEqual(self.post({"transcript": "Rice"}).status_code, 503)

    def test_provider_error_returns_502(self):
        self.client.force_login(self.donor)
        with patch("donations.voice_views.DonationVoiceParser.parse", side_effect=VoiceProviderError("down")):
            response = self.post({"transcript": "Rice"})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "down")
