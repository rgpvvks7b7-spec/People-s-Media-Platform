from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from artists.models import ArtistProfile


User = get_user_model()


class StripeConnectTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="connect_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Connect Artist")
        self.client.force_authenticate(self.artist)

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_demo_connect_onboarding_returns_url(self):
        response = self.client.post("/api/artists/connect/onboarding/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["demo_mode"])
        self.assertIn("connect=demo", response.data["onboarding_url"])

        status_response = self.client.get("/api/artists/connect/status/")
        self.assertEqual(status_response.status_code, 200)
        self.assertTrue(status_response.data["connected"])
