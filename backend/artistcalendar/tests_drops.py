from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from artists.models import ArtistFanContact, ArtistProfile
from mediahub.models import MusicUpload
from notifications.models import Notification
from subscriptions.models import FanSubscription

from .models import ArtistCalendarItem

User = get_user_model()


class DropsTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.artist = User.objects.create_user(
            username="drop_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Drop Artist")
        self.supporter = User.objects.create_user(
            username="drop_supporter",
            password="password123",
            user_type=User.FAN,
            email="supporter@example.com",
        )
        self.fan = User.objects.create_user(
            username="drop_fan",
            password="password123",
            user_type=User.FAN,
        )
        FanSubscription.objects.create(
            fan=self.supporter,
            artist=self.artist,
            monthly_amount="3.00",
            active=True,
        )
        self.track = MusicUpload.objects.create(
            artist=self.artist,
            title="Unreleased Single",
            audio_file=SimpleUploadedFile("single.mp3", b"fake-audio-bytes"),
            is_subscriber_only=False,
            preview_enabled=True,
        )

    def create_drop(self, *, hours_from_now=48, early_hours=24, visibility=ArtistCalendarItem.PUBLIC):
        return ArtistCalendarItem.objects.create(
            artist=self.artist,
            title="Single drop",
            starts_at=timezone.now() + timedelta(hours=hours_from_now),
            item_type=ArtistCalendarItem.RELEASE,
            visibility=visibility,
            supporter_early_hours=early_hours,
            music_upload=self.track,
        )

    def get_track_payload(self, user=None):
        if user:
            self.client.force_authenticate(user)
        else:
            self.client.force_authenticate(None)
        response = self.client.get("/api/media/")
        self.assertEqual(response.status_code, 200)
        tracks = response.data["results"] if isinstance(response.data, dict) else response.data
        return next(item for item in tracks if item["id"] == self.track.id)

    def test_track_without_drop_is_open(self):
        payload = self.get_track_payload(self.fan)
        self.assertTrue(payload["can_access"])
        self.assertIsNone(payload["drop"])

    def test_pending_drop_locks_track_for_everyone_but_owner(self):
        self.create_drop(hours_from_now=72, early_hours=24)

        fan_payload = self.get_track_payload(self.fan)
        self.assertFalse(fan_payload["can_access"])
        self.assertIsNone(fan_payload["audio_file"])
        self.assertTrue(fan_payload["can_preview"])
        self.assertIn("Drops", fan_payload["access_message"])
        self.assertIn("Supporters unlock", fan_payload["access_message"])
        self.assertFalse(fan_payload["drop"]["unlocked"])

        supporter_payload = self.get_track_payload(self.supporter)
        self.assertFalse(supporter_payload["can_access"])
        self.assertFalse(supporter_payload["drop"]["supporter_window_open"])

        owner_payload = self.get_track_payload(self.artist)
        self.assertTrue(owner_payload["can_access"])
        self.assertTrue(owner_payload["drop"]["unlocked"])

    def test_supporter_unlocks_during_early_window(self):
        self.create_drop(hours_from_now=12, early_hours=24)

        supporter_payload = self.get_track_payload(self.supporter)
        self.assertTrue(supporter_payload["can_access"])
        self.assertTrue(supporter_payload["drop"]["unlocked"])

        fan_payload = self.get_track_payload(self.fan)
        self.assertFalse(fan_payload["can_access"])

    def test_stream_endpoint_enforces_drop_lock(self):
        from config.media_access import build_media_stream_token

        self.create_drop(hours_from_now=72, early_hours=24)
        token = build_media_stream_token(self.track.id, "full")

        self.client.force_authenticate(self.fan)
        blocked = self.client.get(f"/api/media/tracks/{self.track.id}/stream/?token={token}")
        self.assertEqual(blocked.status_code, 403)
        self.assertIn("Drops", blocked.data["error"])

        preview_token = build_media_stream_token(self.track.id, "preview")
        preview = self.client.get(f"/api/media/tracks/{self.track.id}/stream/?token={preview_token}")
        self.assertEqual(preview.status_code, 200)

        self.client.force_authenticate(self.artist)
        owner = self.client.get(f"/api/media/tracks/{self.track.id}/stream/?token={token}")
        self.assertEqual(owner.status_code, 200)

    def test_past_drop_no_longer_locks(self):
        ArtistCalendarItem.objects.create(
            artist=self.artist,
            title="Yesterday's drop",
            starts_at=timezone.now() - timedelta(hours=2),
            item_type=ArtistCalendarItem.RELEASE,
            visibility=ArtistCalendarItem.PUBLIC,
            music_upload=self.track,
        )
        payload = self.get_track_payload(self.fan)
        self.assertTrue(payload["can_access"])
        self.assertIsNone(payload["drop"])

    def test_announce_drop_notifies_opted_in_supporters(self):
        contact = ArtistFanContact.objects.create(fan=self.supporter, artist=self.artist)
        contact.share(source=ArtistFanContact.SUPPORT_PROMPT)
        contact.save()

        self.client.force_authenticate(self.artist)
        starts_at = timezone.now() + timedelta(days=3)
        response = self.client.post("/api/artists/calendar/", {
            "title": "Single drop",
            "starts_at": starts_at.isoformat(),
            "item_type": "release",
            "visibility": "public",
            "supporter_early_hours": 24,
            "music_upload_id": self.track.id,
            "announce_drop": "true",
        }, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["announced"], 1)
        note = Notification.objects.get(recipient=self.supporter, notification_type=Notification.MUSIC)
        self.assertIn("Drop announced", note.title)
        self.assertIn("24 hours early", note.body)

    def test_announce_skipped_without_flag_or_for_private(self):
        contact = ArtistFanContact.objects.create(fan=self.supporter, artist=self.artist)
        contact.share(source=ArtistFanContact.SUPPORT_PROMPT)
        contact.save()

        self.client.force_authenticate(self.artist)
        starts_at = timezone.now() + timedelta(days=3)
        silent = self.client.post("/api/artists/calendar/", {
            "title": "Quiet drop",
            "starts_at": starts_at.isoformat(),
            "item_type": "release",
            "visibility": "public",
        }, format="json")
        self.assertEqual(silent.data["announced"], 0)

        private = self.client.post("/api/artists/calendar/", {
            "title": "Private plan",
            "starts_at": starts_at.isoformat(),
            "item_type": "release",
            "visibility": "private",
            "announce_drop": "true",
        }, format="json")
        self.assertEqual(private.data["announced"], 0)
        self.assertFalse(
            Notification.objects.filter(recipient=self.supporter, notification_type=Notification.MUSIC).exists()
        )
