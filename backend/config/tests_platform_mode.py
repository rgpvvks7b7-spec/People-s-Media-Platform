from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import User


def register_payload(**fields):
    payload = {"terms_accepted": True}
    payload.update(fields)
    return payload


@override_settings(PLATFORM_MODE="prelaunch")
class PrelaunchPlatformModeTests(APITestCase):
    def test_health_reports_prelaunch(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["platform_mode"], "prelaunch")
        self.assertFalse(response.json()["fan_registration_open"])
        self.assertFalse(response.json()["fan_experience_open"])

    def test_fan_registration_blocked_in_prelaunch(self):
        response = self.client.post(
            "/api/accounts/register/",
            register_payload(
                username="prelaunch_fan",
                password="password123",
                display_name="Prelaunch Fan",
                email="prelaunch_fan@example.com",
                user_type=User.FAN,
                favorite_genres="indie pop",
                discovery_location="Melbourne",
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "prelaunch_fan_registration_closed")

    def test_artist_registration_allowed_in_prelaunch(self):
        response = self.client.post(
            "/api/accounts/register/",
            register_payload(
                username="prelaunch_artist",
                password="password123",
                display_name="Prelaunch Artist",
                email="prelaunch_artist@example.com",
                user_type=User.ARTIST,
                stage_name="Prelaunch Artist",
                genre="indie pop",
                city="Melbourne",
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["user"]["user_type"], User.ARTIST)

    def test_discovery_blocked_for_guests_in_prelaunch(self):
        response = self.client.get("/api/discovery/artists/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "prelaunch_fan_gated")

    def test_fan_waitlist_join_in_prelaunch(self):
        response = self.client.post(
            "/api/accounts/waitlist/",
            {
                "email": "waitlist_fan@example.com",
                "city": "Melbourne",
                "favorite_genres": "indie pop",
                "terms_accepted": True,
            },
            format="json",
        )
        self.assertIn(response.status_code, {200, 201})
        self.assertEqual(response.json()["entry"]["email"], "waitlist_fan@example.com")

    def test_fan_waitlist_requires_terms(self):
        response = self.client.post(
            "/api/accounts/waitlist/",
            {"email": "no_terms@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


@override_settings(PLATFORM_MODE="live")
class LivePlatformModeTests(APITestCase):
    def test_health_reports_live(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.json()["platform_mode"], "live")
        self.assertTrue(response.json()["fan_registration_open"])

    def test_fan_registration_allowed_when_live(self):
        response = self.client.post(
            "/api/accounts/register/",
            register_payload(
                username="live_fan",
                password="password123",
                display_name="Live Fan",
                email="live_fan@example.com",
                user_type=User.FAN,
                favorite_genres="indie pop",
                discovery_location="Melbourne",
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_fan_waitlist_closed_when_live(self):
        response = self.client.post(
            "/api/accounts/waitlist/",
            {
                "email": "live_waitlist@example.com",
                "terms_accepted": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "waitlist_closed")
