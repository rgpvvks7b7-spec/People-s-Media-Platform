from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from artists.models import ArtistProfile
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
        self.artist_two = User.objects.create_user(
            username="artist_two",
            password="password123",
            user_type=User.ARTIST,
        )
        self.other_fan = User.objects.create_user(
            username="other_fan",
            password="password123",
            user_type=User.FAN,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Artist")
        ArtistProfile.objects.create(owner=self.artist_two, stage_name="Artist Two")

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

    def test_subscription_list_is_empty_for_anonymous_users(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, monthly_amount="2.00")

        response = self.client.get("/api/subscriptions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["subscriptions"], [])
        self.assertEqual(response.data["fan_totals"], {})
        self.assertEqual(response.data["artist_totals"], {})

    def test_fan_subscription_list_only_returns_their_own_supports(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, monthly_amount="2.00")
        FanSubscription.objects.create(fan=self.other_fan, artist=self.artist_two, monthly_amount="4.00")
        self.client.force_authenticate(self.fan)

        response = self.client.get("/api/subscriptions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["subscriptions"]), 1)
        self.assertEqual(response.data["subscriptions"][0]["fan"], "fan")
        self.assertEqual(response.data["fan_totals"], {"fan": "2.00"})
        self.assertEqual(response.data["artist_totals"], {"artist": "1.80"})

    def test_artist_subscription_list_only_returns_their_supporters(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, monthly_amount="2.00")
        FanSubscription.objects.create(fan=self.other_fan, artist=self.artist_two, monthly_amount="4.00")
        self.client.force_authenticate(self.artist)

        response = self.client.get("/api/subscriptions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["subscriptions"]), 1)
        self.assertEqual(response.data["subscriptions"][0]["artist"], "artist")
        self.assertEqual(response.data["fan_totals"], {"fan": "2.00"})
        self.assertEqual(response.data["artist_totals"], {"artist": "1.80"})

    def test_checkout_rejects_non_artist_target_and_invalid_amount(self):
        self.client.force_authenticate(self.fan)

        non_artist_response = self.client.post(
            "/api/subscriptions/checkout/",
            {"artist_id": self.other_fan.id, "monthly_amount": "2.00"},
            format="json",
        )
        invalid_amount_response = self.client.post(
            "/api/subscriptions/checkout/",
            {"artist_id": self.artist.id, "monthly_amount": "not-money"},
            format="json",
        )

        self.assertEqual(non_artist_response.status_code, 400)
        self.assertEqual(invalid_amount_response.status_code, 400)
        self.assertFalse(FanSubscription.objects.filter(fan=self.fan, artist=self.other_fan).exists())

    def test_direct_subscribe_validates_artist_amount_and_billing_date(self):
        self.client.force_authenticate(self.fan)

        bad_artist_response = self.client.post(
            "/api/subscriptions/subscribe/",
            {"artist_id": self.other_fan.id, "monthly_amount": "2.00", "billing_date": 1},
            format="json",
        )
        bad_amount_response = self.client.post(
            "/api/subscriptions/subscribe/",
            {"artist_id": self.artist.id, "monthly_amount": "abc", "billing_date": 1},
            format="json",
        )
        bad_billing_date_response = self.client.post(
            "/api/subscriptions/subscribe/",
            {"artist_id": self.artist.id, "monthly_amount": "2.00", "billing_date": 32},
            format="json",
        )

        self.assertEqual(bad_artist_response.status_code, 400)
        self.assertEqual(bad_amount_response.status_code, 400)
        self.assertEqual(bad_billing_date_response.status_code, 400)
        self.assertFalse(FanSubscription.objects.filter(fan=self.fan, artist=self.artist).exists())
