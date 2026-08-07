
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from artists.models import ArtistProfile
from subscriptions.models import FanSubscription


User = get_user_model()


@override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
class SubscriptionLimitTests(APITestCase):
    def setUp(self):
        self.fan = User.objects.create_user(
            username="cap_fan",
            password="password123",
            user_type=User.FAN,
            subscription_limit=2,
        )
        self.artists = []
        for index in range(3):
            artist = User.objects.create_user(
                username=f"cap_artist_{index}",
                password="password123",
                user_type=User.ARTIST,
            )
            ArtistProfile.objects.create(owner=artist, stage_name=f"Cap Artist {index}")
            self.artists.append(artist)

    def _checkout(self, artist):
        self.client.force_authenticate(self.fan)
        return self.client.post("/api/subscriptions/checkout/", {
            "artist_id": artist.id,
            "profession": "music",
            "monthly_amount": "5.00",
        }, format="json")

    def test_checkout_blocked_at_subscription_limit(self):
        first = self._checkout(self.artists[0])
        second = self._checkout(self.artists[1])
        blocked = self._checkout(self.artists[2])
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.data["code"], "subscription_limit_reached")
        self.assertEqual(blocked.data["limit"], 2)

    def test_extend_limit_allows_additional_support(self):
        self._checkout(self.artists[0])
        self._checkout(self.artists[1])
        blocked = self._checkout(self.artists[2])
        self.assertEqual(blocked.status_code, 403)

        self.client.force_authenticate(self.fan)
        extended = self.client.post("/api/subscriptions/extend-limit/", {"amount": 25}, format="json")
        self.assertEqual(extended.status_code, 200)
        self.assertEqual(extended.data["subscription_limit"], 27)

        allowed = self._checkout(self.artists[2])
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(FanSubscription.objects.filter(fan=self.fan, active=True).count(), 3)

    def test_current_user_exposes_subscription_slots(self):
        self._checkout(self.artists[0])
        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/accounts/current-user/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["subscription_limit"], 2)
        self.assertEqual(response.data["user"]["subscription_count"], 1)
