from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from artists.models import ArtistProfile
from config.media_access import build_media_stream_token
from mediahub.models import MusicUpload
from subscriptions.models import FanSubscription


User = get_user_model()


class StreamAccessTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="stream_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        self.fan = User.objects.create_user(
            username="stream_fan",
            password="password123",
            user_type=User.FAN,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Stream Artist")
        self.track = MusicUpload.objects.create(
            artist=self.artist,
            title="Locked Track",
            audio_file=SimpleUploadedFile("locked.mp3", b"fake-audio-bytes"),
            is_subscriber_only=True,
            preview_enabled=True,
        )

    def test_stream_rejects_missing_token(self):
        response = self.client.get(f"/api/media/tracks/{self.track.id}/stream/")
        self.assertEqual(response.status_code, 403)

    def test_preview_stream_works_without_login(self):
        token = build_media_stream_token(self.track.id, "preview")
        response = self.client.get(f"/api/media/tracks/{self.track.id}/stream/?token={token}")
        self.assertEqual(response.status_code, 200)

    def test_full_stream_requires_subscription(self):
        token = build_media_stream_token(self.track.id, "full")
        response = self.client.get(f"/api/media/tracks/{self.track.id}/stream/?token={token}")
        self.assertEqual(response.status_code, 403)

    def test_full_stream_works_for_subscriber(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, active=True)
        self.client.force_authenticate(self.fan)
        token = build_media_stream_token(self.track.id, "full")
        response = self.client.get(f"/api/media/tracks/{self.track.id}/stream/?token={token}")
        self.assertEqual(response.status_code, 200)
