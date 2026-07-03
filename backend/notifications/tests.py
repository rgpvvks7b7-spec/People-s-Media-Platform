from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from notifications.models import Notification


User = get_user_model()


class NotificationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fan", password="password123", user_type=User.FAN)
        Notification.objects.create(recipient=self.user, title="New track", body="Artist uploaded music")

    def test_user_can_list_and_mark_notifications_read(self):
        self.client.force_authenticate(self.user)

        list_response = self.client.get("/api/notifications/")
        mark_response = self.client.post("/api/notifications/mark-read/", {}, format="json")
        updated_list_response = self.client.get("/api/notifications/")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["unread_count"], 1)
        self.assertEqual(mark_response.data["updated"], 1)
        self.assertEqual(updated_list_response.data["unread_count"], 0)

    def test_user_can_clear_one_or_all_notifications(self):
        second = Notification.objects.create(recipient=self.user, title="Another alert", body="More activity")
        self.client.force_authenticate(self.user)

        clear_one = self.client.post(
            "/api/notifications/clear/",
            {"id": second.id},
            format="json",
        )
        self.assertEqual(clear_one.status_code, 200)
        self.assertEqual(clear_one.data["deleted"], 1)
        self.assertEqual(Notification.objects.filter(recipient=self.user).count(), 1)

        clear_all = self.client.post("/api/notifications/clear/", {}, format="json")
        self.assertEqual(clear_all.status_code, 200)
        self.assertEqual(clear_all.data["deleted"], 1)
        self.assertEqual(Notification.objects.filter(recipient=self.user).count(), 0)
        self.assertEqual(clear_all.data["unread_count"], 0)
