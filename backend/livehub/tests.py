from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from livehub.models import LiveSession
from notifications.models import Notification
from subscriptions.models import FanSubscription


User = get_user_model()


class LiveSessionTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(username="artist", password="password123", user_type=User.ARTIST)
        self.fan = User.objects.create_user(username="fan", password="password123", user_type=User.FAN)
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, active=True)

    def test_artist_can_start_live_and_notify_supporters(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/live/start/",
            {"title": "Studio session", "description": "Testing live", "access_mode": LiveSession.PREVIEW_30},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(LiveSession.objects.filter(artist=self.artist, is_live=True).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.fan, notification_type=Notification.LIVE).exists())

    def test_live_chat_requires_authentication(self):
        self.client.force_authenticate(self.artist)
        start_response = self.client.post("/api/live/start/", {"title": "Studio session"}, format="json")
        session_id = start_response.data["session"]["id"]

        self.client.force_authenticate(user=None)
        blocked_response = self.client.post(f"/api/live/{session_id}/chat/", {"body": "hello"}, format="json")

        self.client.force_authenticate(self.fan)
        allowed_response = self.client.post(f"/api/live/{session_id}/chat/", {"body": "hello"}, format="json")

        self.assertEqual(blocked_response.status_code, 401)
        self.assertEqual(allowed_response.status_code, 201)

    def test_only_owner_can_stop_live(self):
        self.client.force_authenticate(self.artist)
        start_response = self.client.post("/api/live/start/", {"title": "Studio session"}, format="json")
        session_id = start_response.data["session"]["id"]

        self.client.force_authenticate(self.fan)
        blocked_response = self.client.post(f"/api/live/{session_id}/stop/", {}, format="json")

        self.client.force_authenticate(self.artist)
        allowed_response = self.client.post(f"/api/live/{session_id}/stop/", {}, format="json")

        self.assertEqual(blocked_response.status_code, 403)
        self.assertEqual(allowed_response.status_code, 200)
        self.assertFalse(LiveSession.objects.get(id=session_id).is_live)
