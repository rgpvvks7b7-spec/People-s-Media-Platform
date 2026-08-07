import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from livehub.models import LiveSession
from mediahub.models import MusicUpload
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


_MEDIA_ROOT = tempfile.mkdtemp(prefix="livehub-test-media-")


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class ListeningPartyTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.artist = User.objects.create_user(username="artist", password="password123", user_type=User.ARTIST)
        self.other_artist = User.objects.create_user(username="rival", password="password123", user_type=User.ARTIST)
        self.supporter = User.objects.create_user(username="supporter", password="password123", user_type=User.FAN)
        self.free_fan = User.objects.create_user(username="freefan", password="password123", user_type=User.FAN)
        FanSubscription.objects.create(fan=self.supporter, artist=self.artist, active=True)

        self.track = MusicUpload.objects.create(
            artist=self.artist,
            title="Unreleased Anthem",
            audio_file=SimpleUploadedFile("anthem.mp3", b"party-audio", content_type="audio/mpeg"),
            is_subscriber_only=True,
        )

    def start_party(self, access_mode=LiveSession.PUBLIC):
        self.client.force_authenticate(self.artist)
        response = self.client.post(
            "/api/live/start/",
            {"title": "First listen", "track_id": self.track.id, "access_mode": access_mode},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return response.data["session"]

    def test_start_party_with_track_serializes_track(self):
        session = self.start_party()

        self.assertEqual(session["track"]["id"], self.track.id)
        self.assertEqual(session["track"]["title"], "Unreleased Anthem")

        notification = Notification.objects.filter(recipient=self.supporter, notification_type=Notification.LIVE).first()
        self.assertIsNotNone(notification)
        self.assertIn("listening party", notification.title)
        self.assertEqual(notification.target_url, "/?page=live")

    def test_cannot_start_party_with_foreign_track(self):
        self.client.force_authenticate(self.other_artist)
        response = self.client.post(
            "/api/live/start/",
            {"title": "Stolen listen", "track_id": self.track.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Track not found in your library")

    def test_detail_gives_stream_url_to_logged_in_fan_but_not_guest(self):
        session = self.start_party()

        self.client.force_authenticate(user=None)
        guest_response = self.client.get(f"/api/live/{session['id']}/")
        self.assertEqual(guest_response.status_code, 200)
        self.assertFalse(guest_response.data["viewer_can_join"])
        self.assertEqual(guest_response.data["join_requirement"], "account")
        self.assertIsNone(guest_response.data["stream_url"])

        self.client.force_authenticate(self.free_fan)
        fan_response = self.client.get(f"/api/live/{session['id']}/")
        self.assertTrue(fan_response.data["viewer_can_join"])
        self.assertEqual(fan_response.data["join_requirement"], "")
        self.assertIn("/stream/?token=", fan_response.data["stream_url"])

    def test_supporters_only_party_gates_non_supporters(self):
        session = self.start_party(access_mode=LiveSession.SUPPORTERS)

        self.client.force_authenticate(self.free_fan)
        fan_response = self.client.get(f"/api/live/{session['id']}/")
        self.assertFalse(fan_response.data["viewer_can_join"])
        self.assertEqual(fan_response.data["join_requirement"], "supporter")
        self.assertIsNone(fan_response.data["stream_url"])

        chat_response = self.client.post(f"/api/live/{session['id']}/chat/", {"body": "let me in"}, format="json")
        self.assertEqual(chat_response.status_code, 403)

        self.client.force_authenticate(self.supporter)
        supporter_response = self.client.get(f"/api/live/{session['id']}/")
        self.assertTrue(supporter_response.data["viewer_can_join"])
        self.assertIn("/stream/?token=", supporter_response.data["stream_url"])

    def test_party_unlocks_full_stream_only_while_live(self):
        session = self.start_party()

        self.client.force_authenticate(self.free_fan)
        detail = self.client.get(f"/api/live/{session['id']}/")
        stream_url = detail.data["stream_url"]

        live_stream = self.client.get(stream_url)
        self.assertEqual(live_stream.status_code, 200)

        self.client.force_authenticate(self.artist)
        self.client.post(f"/api/live/{session['id']}/stop/", {}, format="json")

        self.client.force_authenticate(self.free_fan)
        ended_stream = self.client.get(stream_url)
        self.assertEqual(ended_stream.status_code, 403)
        self.assertEqual(ended_stream.data["error"], "Subscription required")

    def test_detail_after_param_returns_only_new_messages(self):
        session = self.start_party()

        self.client.force_authenticate(self.free_fan)
        first = self.client.post(f"/api/live/{session['id']}/chat/", {"body": "first"}, format="json")
        second = self.client.post(f"/api/live/{session['id']}/chat/", {"body": "second"}, format="json")
        first_id = first.data["message"]["id"]

        response = self.client.get(f"/api/live/{session['id']}/?after={first_id}")

        bodies = [message["body"] for message in response.data["messages"]]
        self.assertEqual(bodies, ["second"])
        self.assertEqual(response.data["messages"][0]["id"], second.data["message"]["id"])
