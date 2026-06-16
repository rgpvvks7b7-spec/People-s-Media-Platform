from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from marketplace.models import Product
from subscriptions.models import FanSubscription


User = get_user_model()


class MarketplaceAccessTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="artist",
            password="password123",
            user_type=User.ARTIST,
        )
        self.fan = User.objects.create_user(
            username="fan",
            password="password123",
            user_type=User.FAN,
        )
        self.product = Product.objects.create(
            artist=self.artist,
            product_type=Product.SAMPLE_PACK,
            title="Supporter Pack",
            price="5.00",
            is_supporter_only=True,
            preview_audio="marketplace/previews/preview.mp3",
            product_file="marketplace/files/pack.zip",
        )

    def get_product_payload(self):
        response = self.client.get("/api/marketplace/")
        self.assertEqual(response.status_code, 200)
        return next(product for product in response.data if product["id"] == self.product.id)

    def test_supporter_only_files_are_hidden_until_active_support(self):
        anonymous_payload = self.get_product_payload()

        FanSubscription.objects.create(fan=self.fan, artist=self.artist, active=True)
        self.client.force_authenticate(self.fan)
        supporter_payload = self.get_product_payload()

        self.assertFalse(anonymous_payload["can_access"])
        self.assertIsNone(anonymous_payload["preview_audio"])
        self.assertIsNone(anonymous_payload["product_file"])
        self.assertTrue(supporter_payload["can_access"])
        self.assertIn("/media/marketplace/previews/preview.mp3", supporter_payload["preview_audio"])
        self.assertIn("/media/marketplace/files/pack.zip", supporter_payload["product_file"])

    def test_inactive_subscription_does_not_unlock_supporter_only_files(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, active=False)
        self.client.force_authenticate(self.fan)

        payload = self.get_product_payload()

        self.assertFalse(payload["can_access"])
        self.assertIsNone(payload["preview_audio"])
        self.assertIsNone(payload["product_file"])

    def test_fans_cannot_create_products_but_artists_can(self):
        self.client.force_authenticate(self.fan)
        fan_response = self.client.post(
            "/api/marketplace/create/",
            {"title": "Fan Product", "price": "2.00"},
            format="multipart",
        )

        self.client.force_authenticate(self.artist)
        artist_response = self.client.post(
            "/api/marketplace/create/",
            {"title": "Artist Product", "price": "2.00"},
            format="multipart",
        )

        self.assertEqual(fan_response.status_code, 403)
        self.assertEqual(artist_response.status_code, 201)
        self.assertTrue(Product.objects.filter(title="Artist Product", artist=self.artist).exists())
