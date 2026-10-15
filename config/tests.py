from django.conf import settings
from django.test import SimpleTestCase, override_settings

from .context_processors import map_settings


class MapConfigurationTests(SimpleTestCase):
    def test_cross_origin_requests_send_only_the_site_origin(self):
        self.assertEqual(settings.SECURE_REFERRER_POLICY, "strict-origin-when-cross-origin")
        response = self.client.get("/health/")
        self.assertEqual(response["Referrer-Policy"], "strict-origin-when-cross-origin")

    @override_settings(
        MAP_TILE_URL="https://tiles.example.test/{z}/{x}/{y}.png",
        MAP_TILE_ATTRIBUTION="Example Maps",
    )
    def test_map_settings_are_exposed_to_dashboard_templates(self):
        self.assertEqual(
            map_settings(None),
            {
                "MAP_TILE_URL": "https://tiles.example.test/{z}/{x}/{y}.png",
                "MAP_TILE_ATTRIBUTION": "Example Maps",
                "PAYMENTS_ENABLED": settings.PAYMENTS_ENABLED,
            },
        )
