from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from subscriptions.models import FanSubscription


User = get_user_model()


class DemoSupportFallbackTests(APITestCase):
    def setUp(self):
        self.fan = User.objects.create_user(
            username="fan",
            password="password123",
            user_type=User.FAN,
        )
        self.artist = User.objects.create_user(
            username="artist",
            password="password123",
            user_type=User.ARTIST,
        )

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_checkout_creates_demo_subscription_without_stripe_keys(self):
        self.client.force_authenticate(self.fan)

        response = self.client.post(
            "/api/subscriptions/checkout/",
            {"artist_id": self.artist.id, "monthly_amount": "2.50"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["demo"])
        self.assertTrue(
            FanSubscription.objects.filter(
                fan=self.fan,
                artist=self.artist,
                active=True,
                payment_provider="demo",
            ).exists()
        )
