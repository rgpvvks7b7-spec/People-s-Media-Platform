from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from artists.models import ArtistFanContact, ArtistProfile, FanJourneyEvent
from mediahub.models import ArtworkUpload, FanPlaylist, FanPlaylistTrack, MusicUpload, SongCoverArt
from notifications.models import Notification
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
        ArtistProfile.objects.create(owner=self.artist, stage_name="Artist", professions="music,visual_art")
        self.track = MusicUpload.objects.create(
            artist=self.artist,
            title="Private Track",
            audio_file="music/private-track.mp3",
            is_subscriber_only=True,
            allow_fan_radio=True,
        )

    def get_track_payload(self):
        response = self.client.get("/api/media/")
        self.assertEqual(response.status_code, 200)
        return next(track for track in response.data if track["id"] == self.track.id)

    def test_anonymous_user_does_not_receive_supporter_only_audio_url(self):
        payload = self.get_track_payload()

        self.assertFalse(payload["can_access"])
        self.assertIsNone(payload["audio_file"])
        self.assertTrue(payload["can_preview"])
        self.assertIn(f"/api/media/tracks/{self.track.id}/stream/", payload["preview_audio_file"])
        self.assertIn("token=", payload["preview_audio_file"])
        self.assertEqual(payload["access_message"], "Subscribe to unlock full track. Preview available for 30s.")

    def test_active_supporter_receives_supporter_only_audio_url(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, active=True)
        self.client.force_authenticate(self.fan)

        payload = self.get_track_payload()

        self.assertTrue(payload["can_access"])
        self.assertIn(f"/api/media/tracks/{self.track.id}/stream/", payload["audio_file"])
        self.assertIn("token=", payload["audio_file"])

    def test_inactive_subscription_does_not_unlock_supporter_only_audio(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, active=False)
        self.client.force_authenticate(self.fan)

        payload = self.get_track_payload()

        self.assertFalse(payload["can_access"])
        self.assertIsNone(payload["audio_file"])

    def test_support_for_other_profession_does_not_unlock_music_audio(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, profession="visual_art", active=True)
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

    def test_artist_can_upload_music_branch_profession_track(self):
        self.artist.artist_profile.professions = "music,comedy"
        self.artist.artist_profile.save(update_fields=["professions"])
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/media/create/",
            {
                "profession": "comedy",
                "title": "New Five",
                "audio_file": SimpleUploadedFile("set.mp3", b"audio"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        track = MusicUpload.objects.get(title="New Five")
        self.assertEqual(track.profession, "comedy")

    def test_radio_only_includes_artist_opted_in_accessible_tracks(self):
        MusicUpload.objects.create(
            artist=self.artist,
            title="Playlist Only",
            audio_file="music/playlist-only.mp3",
            allow_fan_radio=False,
            is_subscriber_only=False,
        )

        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/media/radio/")

        titles = {track["title"] for track in response.data["results"]}
        self.assertNotIn("Private Track", titles)
        self.assertNotIn("Playlist Only", titles)

        FanSubscription.objects.create(fan=self.fan, artist=self.artist, profession="music", active=True)
        response = self.client.get("/api/media/radio/")
        titles = {track["title"] for track in response.data["results"]}

        self.assertIn("Private Track", titles)
        self.assertNotIn("Playlist Only", titles)

    def test_fan_playlist_can_include_accessible_track_even_when_not_radio_enabled(self):
        playlist_only = MusicUpload.objects.create(
            artist=self.artist,
            title="Playlist Only",
            audio_file="music/playlist-only.mp3",
            allow_fan_radio=False,
            is_subscriber_only=False,
        )
        self.client.force_authenticate(self.fan)

        create_response = self.client.post(
            "/api/media/playlists/",
            {"title": "My Fan Mix"},
            format="json",
        )
        add_response = self.client.post(
            f"/api/media/playlists/{create_response.data['playlist']['id']}/add-track/",
            {"track_id": playlist_only.id},
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(add_response.status_code, 200)
        self.assertEqual(add_response.data["playlist"]["tracks"][0]["title"], "Playlist Only")
        self.assertTrue(FanPlaylistTrack.objects.filter(track=playlist_only).exists())

    def test_playlist_rejects_inaccessible_supporter_only_track(self):
        playlist = FanPlaylist.objects.create(owner=self.fan, title="Locked Mix")
        self.client.force_authenticate(self.fan)

        response = self.client.post(
            f"/api/media/playlists/{playlist.id}/add-track/",
            {"track_id": self.track.id},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(FanPlaylistTrack.objects.filter(playlist=playlist, track=self.track).exists())

    def test_music_play_events_are_logged_for_accessible_tracks(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, profession="music", active=True)
        self.client.force_authenticate(self.fan)

        preview_response = self.client.post(
            "/api/media/events/",
            {
                "track_id": self.track.id,
                "event_type": FanJourneyEvent.MUSIC_PREVIEW,
                "seconds_played": 3,
            },
            format="json",
        )
        full_response = self.client.post(
            "/api/media/events/",
            {
                "track_id": self.track.id,
                "event_type": FanJourneyEvent.MUSIC_FULL_PLAY,
                "seconds_played": 90,
            },
            format="json",
        )
        owner_tracks_response = self.client.get("/api/media/")

        self.assertEqual(preview_response.status_code, 201)
        self.assertEqual(full_response.status_code, 201)
        self.assertEqual(
            FanJourneyEvent.objects.filter(
                fan=self.fan,
                artist=self.artist,
                music_upload=self.track,
            ).count(),
            2,
        )

        self.client.force_authenticate(self.artist)
        owner_tracks_response = self.client.get("/api/media/")
        payload = next(track for track in owner_tracks_response.data if track["id"] == self.track.id)
        self.assertEqual(payload["funnel"]["preview_plays"], 1)
        self.assertEqual(payload["funnel"]["full_plays"], 1)

    def test_artist_upload_defaults_to_preview_funnel_and_notifies_on_seal(self):
        ArtistFanContact.objects.create(
            fan=self.fan,
            artist=self.artist,
            email_shared=True,
            source=ArtistFanContact.SUPPORT_PROMPT,
        )
        self.artist.artist_profile.is_verified = True
        self.artist.artist_profile.save(update_fields=["is_verified"])
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/media/create/",
            {
                "title": "Preview First",
                "audio_file": SimpleUploadedFile("preview.mp3", b"audio"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        track = MusicUpload.objects.get(title="Preview First")
        self.assertTrue(track.is_subscriber_only)
        self.assertTrue(track.preview_enabled)
        self.assertEqual(track.preview_seconds, 30)

        # Notification is deferred until the artist seals the release.
        self.assertFalse(
            Notification.objects.filter(recipient=self.fan, notification_type=Notification.MUSIC).exists()
        )

        seal = self.client.post(
            f"/api/originlock/releases/{response.data['release_approval_id']}/seal/",
            {"approval_method": "password_fallback", "password": "password123"},
            format="json",
        )
        self.assertEqual(seal.status_code, 200)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.fan,
                actor=self.artist,
                notification_type=Notification.MUSIC,
                title="New track: Preview First",
            ).exists()
        )

    def test_upload_rejects_fully_ai_generated_track(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/media/create/",
            {
                "title": "Generated Track",
                "audio_file": SimpleUploadedFile("generated.mp3", b"audio"),
                "ai_disclosure_level": MusicUpload.AI_GENERATED,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Fully AI-generated tracks aren’t permitted on IndieFund.")
        self.assertFalse(MusicUpload.objects.filter(title="Generated Track").exists())

    def test_ai_assisted_upload_requires_note(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/media/create/",
            {
                "title": "Missing Note",
                "audio_file": SimpleUploadedFile("missing-note.mp3", b"audio"),
                "ai_disclosure_level": MusicUpload.AI_ASSISTED,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "AI disclosure note is required for assisted or collaborative tracks.")

    def test_ai_disclosure_badge_is_serialized(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/media/create/",
            {
                "title": "Stem Cleanup",
                "audio_file": SimpleUploadedFile("stem-cleanup.mp3", b"audio"),
                "ai_disclosure_level": MusicUpload.AI_ASSISTED,
                "ai_disclosure_note": "Used AI stem cleanup, then arranged and mixed manually.",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        track = MusicUpload.objects.get(title="Stem Cleanup")
        self.assertEqual(track.ai_disclosure_level, MusicUpload.AI_ASSISTED)

        list_response = self.client.get("/api/media/")
        payload = next(item for item in list_response.data if item["id"] == track.id)
        self.assertEqual(payload["ai_disclosure_badge"], "AI-assisted · disclosed")
        self.assertEqual(payload["ai_disclosure_note"], "Used AI stem cleanup, then arranged and mixed manually.")


class ArtworkUploadTests(APITestCase):
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
        ArtistProfile.objects.create(owner=self.artist, stage_name="Artist", professions="music,visual_art")

    def test_artist_can_upload_visual_artwork(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/media/artworks/create/",
            {
                "profession": "visual_art",
                "title": "Blue Study",
                "image": SimpleUploadedFile("blue.jpg", b"image", content_type="image/jpeg"),
                "medium": "Watercolour",
                "dimensions": "A4",
                "year": "2026",
                "availability": ArtworkUpload.PRINT_ONLY,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        artwork = ArtworkUpload.objects.get(title="Blue Study")
        self.assertEqual(artwork.profession, "visual_art")
        self.assertEqual(artwork.medium, "Watercolour")

        list_response = self.client.get("/api/media/artworks/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data[0]["title"], "Blue Study")
        self.assertEqual(list_response.data[0]["availability_label"], "Print only")

    def test_artwork_cannot_be_uploaded_to_music_profession(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/media/artworks/create/",
            {
                "profession": "music",
                "title": "Wrong Side",
                "image": SimpleUploadedFile("wrong.jpg", b"image", content_type="image/jpeg"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Artwork belongs on an arts profession.")

    def test_artwork_cannot_be_uploaded_to_music_branch_profession(self):
        self.artist.artist_profile.professions = "music,comedy"
        self.artist.artist_profile.save(update_fields=["professions"])
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/media/artworks/create/",
            {
                "profession": "comedy",
                "title": "Wrong Side",
                "image": SimpleUploadedFile("wrong.jpg", b"image", content_type="image/jpeg"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Artwork belongs on an arts profession.")


class SongCoverArtTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="artist",
            password="password123",
            user_type=User.ARTIST,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Artist", professions="music")

    def test_artist_can_save_cover_to_library_and_use_it_on_track(self):
        self.client.force_authenticate(self.artist)

        cover_response = self.client.post(
            "/api/media/cover-art/create/",
            {
                "profession": "music",
                "label": "Purple Wave",
                "image": SimpleUploadedFile("cover.jpg", b"cover-image", content_type="image/jpeg"),
                "is_default": "true",
            },
            format="multipart",
        )
        self.assertEqual(cover_response.status_code, 201)
        cover_id = cover_response.data["cover"]["id"]

        track_response = self.client.post(
            "/api/media/create/",
            {
                "profession": "music",
                "title": "Library Cover Track",
                "audio_file": SimpleUploadedFile("track.mp3", b"audio", content_type="audio/mpeg"),
                "library_cover_id": cover_id,
            },
            format="multipart",
        )
        self.assertEqual(track_response.status_code, 201)

        track = MusicUpload.objects.get(title="Library Cover Track")
        self.assertEqual(track.library_cover_id, cover_id)
        self.assertFalse(track.cover_art)

        list_response = self.client.get("/api/media/")
        payload = next(item for item in list_response.data if item["id"] == track.id)
        self.assertIn("/media/cover_art/library/", payload["cover_art"])

    def test_track_without_cover_uses_default_library_cover(self):
        default_cover = SongCoverArt.objects.create(
            artist=self.artist,
            profession="music",
            image=SimpleUploadedFile("default.jpg", b"default-cover", content_type="image/jpeg"),
            label="Default",
            is_default=True,
        )
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/media/create/",
            {
                "profession": "music",
                "title": "Fallback Cover Track",
                "audio_file": SimpleUploadedFile("track.mp3", b"audio", content_type="audio/mpeg"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)

        track = MusicUpload.objects.get(title="Fallback Cover Track")
        self.assertEqual(track.library_cover_id, default_cover.id)


class UploadTrustLimitTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="new_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="New Artist")

    def test_new_incomplete_profile_artist_hits_upload_limit(self):
        self.client.force_authenticate(self.artist)
        for index in range(3):
            response = self.client.post(
                "/api/media/create/",
                {
                    "title": f"Track {index}",
                    "audio_file": SimpleUploadedFile(f"track{index}.mp3", b"audio", content_type="audio/mpeg"),
                },
                format="multipart",
            )
            self.assertEqual(response.status_code, 201)

        blocked = self.client.post(
            "/api/media/create/",
            {
                "title": "Track blocked",
                "audio_file": SimpleUploadedFile("blocked.mp3", b"audio", content_type="audio/mpeg"),
            },
            format="multipart",
        )
        self.assertEqual(blocked.status_code, 403)
        self.assertIn("Complete your profile", blocked.data["error"])

    def test_ai_generated_upload_is_rejected(self):
        self.client.force_authenticate(self.artist)
        response = self.client.post(
            "/api/media/create/",
            {
                "title": "Suno Track",
                "audio_file": SimpleUploadedFile("suno.mp3", b"audio", content_type="audio/mpeg"),
                "ai_disclosure_level": "ai_generated",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Fully AI-generated", response.data["error"])
