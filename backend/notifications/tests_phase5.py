from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from notifications.models import PushSubscription


User = get_user_model()


class PushSubscriptionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="push_fan",
            password="password123",
            user_type=User.FAN,
        )
        self.client.force_authenticate(self.user)

    def test_vapid_public_key_endpoint(self):
        response = self.client.get("/api/notifications/push/vapid/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("enabled", response.data)

    def test_push_subscribe_and_unsubscribe(self):
        payload = {
            "subscription": {
                "endpoint": "https://push.example.test/subscription/1",
                "keys": {"p256dh": "test-p256dh", "auth": "test-auth"},
            }
        }
        subscribe = self.client.post("/api/notifications/push/subscribe/", payload, format="json")
        self.assertEqual(subscribe.status_code, 200)
        self.assertTrue(PushSubscription.objects.filter(user=self.user).exists())

        unsubscribe = self.client.post(
            "/api/notifications/push/unsubscribe/",
            {"endpoint": payload["subscription"]["endpoint"]},
            format="json",
        )
        self.assertEqual(unsubscribe.status_code, 200)
        self.assertFalse(PushSubscription.objects.filter(user=self.user).exists())
