from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from moderation.models import ContentReport, UserBlock
from posts.models import Post


User = get_user_model()


class ModerationTests(APITestCase):
    def setUp(self):
        self.fan = User.objects.create_user(username="mod_fan", password="password123", user_type=User.FAN)
        self.artist = User.objects.create_user(username="mod_artist", password="password123", user_type=User.ARTIST)
        self.admin = User.objects.create_user(
            username="mod_admin",
            password="password123",
            user_type=User.ADMIN,
            is_staff=True,
        )
        self.post = Post.objects.create(author=self.artist, title="Test post", body="Hello")

    def test_fan_can_report_post(self):
        self.client.force_authenticate(self.fan)
        response = self.client.post(
            "/api/moderation/reports/",
            {"target_type": "post", "target_id": self.post.id, "reason": "spam"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(ContentReport.objects.count(), 1)

    def test_block_prevents_duplicate(self):
        self.client.force_authenticate(self.fan)
        payload = {"user_id": self.artist.id}
        first = self.client.post("/api/moderation/blocks/", payload, format="json")
        second = self.client.post("/api/moderation/blocks/", payload, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(UserBlock.objects.count(), 1)

    def test_staff_can_list_open_reports(self):
        ContentReport.objects.create(
            reporter=self.fan,
            target_type=ContentReport.POST,
            target_id=self.post.id,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/moderation/reports/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
