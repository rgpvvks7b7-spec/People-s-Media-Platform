from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from mediahub.models import MusicUpload
from subscriptions.models import FanSubscription


User = get_user_model()


class MusicAccessTests(APITestCase):
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
        self.other_fan = User.objects.create_user(
            username="other_fan",
            password="password123",
            user_type=User.FAN,
        )
        self.track = MusicUpload.objects.create(
            artist=self.artist,
            title="Private Track",
            audio_file="music/private-track.mp3",
            is_subscriber_only=True,
        )

    def get_track_payload(self):
        response = self.client.get("/api/media/")
        self.assertEqual(response.status_code, 200)
        return next(track for track in response.data if track["id"] == self.track.id)

    def test_anonymous_user_does_not_receive_supporter_only_audio_url(self):
        payload = self.get_track_payload()

        self.assertFalse(payload["can_access"])
        self.assertIsNone(payload["audio_file"])
        self.assertEqual(payload["access_message"], "Supporters only")

    def test_active_supporter_receives_supporter_only_audio_url(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, active=True)
        self.client.force_authenticate(self.fan)

        payload = self.get_track_payload()

        self.assertTrue(payload["can_access"])
        self.assertIn("/media/music/private-track.mp3", payload["audio_file"])

    def test_inactive_subscription_does_not_unlock_supporter_only_audio(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, active=False)
        self.client.force_authenticate(self.fan)

        payload = self.get_track_payload()

        self.assertFalse(payload["can_access"])
        self.assertIsNone(payload["audio_file"])

    def test_artist_can_upload_music_but_fan_cannot(self):
        self.client.force_authenticate(self.fan)
        fan_response = self.client.post(
            "/api/media/create/",
            {
                "title": "Fan Upload",
                "audio_file": SimpleUploadedFile("fan.mp3", b"audio"),
            },
            format="multipart",
        )

        self.client.force_authenticate(self.artist)
        artist_response = self.client.post(
            "/api/media/create/",
            {
                "title": "Artist Upload",
                "audio_file": SimpleUploadedFile("artist.mp3", b"audio"),
            },
            format="multipart",
        )

        self.assertEqual(fan_response.status_code, 403)
        self.assertEqual(artist_response.status_code, 201)
        self.assertTrue(MusicUpload.objects.filter(title="Artist Upload", artist=self.artist).exists())
