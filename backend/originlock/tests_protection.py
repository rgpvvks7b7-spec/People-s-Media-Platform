"""Tests for the protected media anti-scraping foundation.

Covers: no raw file URLs in API responses, purchase-gated downloads,
access logging, and abuse flag heuristics.
"""

import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from artists.models import ArtistProfile
from config.media_access import build_file_access_token, build_media_stream_token
from marketplace.models import Product
from marketplace.purchase_flow import complete_product_purchase
from mediahub.models import MusicUpload
from originlock.models import (
    AI_TRAINING_NOT_ALLOWED,
    MediaAbuseFlag,
    MediaAccessLog,
)
from originlock.protection import PROTECTED_WORK_NOTICE
from subscriptions.models import FanSubscription


User = get_user_model()


class RawFileUrlExposureTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="protected_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        self.fan = User.objects.create_user(
            username="protected_fan",
            password="password123",
            user_type=User.FAN,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Protected", professions="music")
        self.track = MusicUpload.objects.create(
            artist=self.artist,
            title="Sealed Song",
            audio_file="music/sealed-song.mp3",
            is_subscriber_only=False,
        )
        self.product = Product.objects.create(
            artist=self.artist,
            product_type=Product.SAMPLE_PACK,
            title="Pack",
            price="5.00",
            preview_audio="marketplace/previews/pack-preview.mp3",
            product_file="marketplace/files/pack.zip",
        )
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, active=True)

    def test_music_list_never_exposes_raw_audio_urls(self):
        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/media/")

        body = json.dumps(response.data, default=str)
        self.assertNotIn("/media/music/", body)

        payload = next(track for track in response.data if track["id"] == self.track.id)
        self.assertIn(f"/api/media/tracks/{self.track.id}/stream/", payload["audio_file"])
        self.assertIn("token=", payload["audio_file"])

    def test_product_list_never_exposes_raw_file_urls(self):
        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/marketplace/")

        body = json.dumps(response.data, default=str)
        self.assertNotIn("/media/marketplace/previews/", body)
        self.assertNotIn("/media/marketplace/files/", body)

        payload = next(item for item in response.data if item["id"] == self.product.id)
        self.assertIn(f"/api/marketplace/files/{self.product.id}/preview/", payload["preview_audio"])

    def test_track_payload_includes_protection_metadata(self):
        response = self.client.get("/api/media/")
        payload = next(track for track in response.data if track["id"] == self.track.id)

        protection = payload["protection"]
        self.assertTrue(protection["is_master_private"])
        self.assertTrue(protection["download_requires_purchase"])
        self.assertEqual(protection["ai_training_consent"], AI_TRAINING_NOT_ALLOWED)
        self.assertTrue(protection["no_ai_training_notice"])
        self.assertIn("Protected Stream", protection["labels"])
        self.assertIn("Do Not Train", protection["labels"])
        self.assertEqual(protection["notice"], PROTECTED_WORK_NOTICE)

    def test_stream_disabled_track_hides_stream_urls(self):
        self.track.public_stream_enabled = False
        self.track.save(update_fields=["public_stream_enabled"])

        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/media/")
        payload = next(track for track in response.data if track["id"] == self.track.id)
        self.assertIsNone(payload["audio_file"])

        token = build_media_stream_token(self.track.id, "full")
        stream = self.client.get(f"/api/media/tracks/{self.track.id}/stream/?token={token}")
        self.assertEqual(stream.status_code, 403)


class PurchaseGatedDownloadTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="download_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        self.fan = User.objects.create_user(
            username="download_fan",
            password="password123",
            user_type=User.FAN,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Downloads", professions="music")
        self.product = Product.objects.create(
            artist=self.artist,
            product_type=Product.SAMPLE_PACK,
            title="Paid Pack",
            price="9.00",
            product_file=SimpleUploadedFile("paid-pack.zip", b"zip-bytes"),
        )

    def download(self):
        token = build_file_access_token("product", self.product.id)
        return self.client.get(f"/api/marketplace/files/{self.product.id}/download/?token={token}")

    def test_download_requires_purchase(self):
        self.client.force_authenticate(self.fan)
        blocked = self.download()
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.data["error"], "Purchase required to download this file.")

        complete_product_purchase(self.fan, self.product)
        allowed = self.download()
        self.assertEqual(allowed.status_code, 200)

    def test_owner_can_always_download(self):
        self.client.force_authenticate(self.artist)
        response = self.download()
        self.assertEqual(response.status_code, 200)

    def test_purchaser_sees_download_url_in_product_list(self):
        self.client.force_authenticate(self.fan)
        before = next(item for item in self.client.get("/api/marketplace/").data if item["id"] == self.product.id)
        self.assertIsNone(before["product_file"])
        self.assertFalse(before["can_download"])

        complete_product_purchase(self.fan, self.product)
        after = next(item for item in self.client.get("/api/marketplace/").data if item["id"] == self.product.id)
        self.assertIn(f"/api/marketplace/files/{self.product.id}/download/", after["product_file"])
        self.assertTrue(after["can_download"])

    def test_artist_can_opt_out_of_purchase_gating(self):
        self.product.download_requires_purchase = False
        self.product.save(update_fields=["download_requires_purchase"])

        self.client.force_authenticate(self.fan)
        response = self.download()
        self.assertEqual(response.status_code, 200)


class MediaAccessLoggingTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="log_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        self.fan = User.objects.create_user(
            username="log_fan",
            password="password123",
            user_type=User.FAN,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Logs", professions="music")
        self.track = MusicUpload.objects.create(
            artist=self.artist,
            title="Logged Track",
            audio_file=SimpleUploadedFile("logged.mp3", b"audio-bytes"),
            is_subscriber_only=False,
        )
        self.product = Product.objects.create(
            artist=self.artist,
            product_type=Product.SAMPLE_PACK,
            title="Logged Pack",
            price="5.00",
            download_requires_purchase=False,
            product_file=SimpleUploadedFile("logged-pack.zip", b"zip-bytes"),
        )

    def stream(self, access="full", user_agent="Mozilla/5.0 (Macintosh) AppleWebKit/605"):
        token = build_media_stream_token(self.track.id, access)
        return self.client.get(
            f"/api/media/tracks/{self.track.id}/stream/?token={token}",
            HTTP_USER_AGENT=user_agent,
        )

    def test_stream_access_is_logged(self):
        self.client.force_authenticate(self.fan)
        response = self.stream()
        self.assertEqual(response.status_code, 200)

        log = MediaAccessLog.objects.get()
        self.assertEqual(log.user, self.fan)
        self.assertEqual(log.artist, self.artist)
        self.assertEqual(log.access_type, MediaAccessLog.STREAM)
        self.assertEqual(log.object_id, self.track.id)
        self.assertTrue(log.user_agent)

    def test_download_access_is_logged(self):
        self.client.force_authenticate(self.fan)
        token = build_file_access_token("product", self.product.id)
        response = self.client.get(
            f"/api/marketplace/files/{self.product.id}/download/?token={token}",
            HTTP_USER_AGENT="Mozilla/5.0 (Macintosh) AppleWebKit/605",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            MediaAccessLog.objects.filter(
                user=self.fan,
                access_type=MediaAccessLog.DOWNLOAD,
                object_id=self.product.id,
            ).exists()
        )

    def test_bot_user_agent_raises_abuse_flag(self):
        response = self.stream(user_agent="python-requests/2.31")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            MediaAbuseFlag.objects.filter(flag_type=MediaAbuseFlag.BOT_LIKE_ACCESS).exists()
        )

    def test_repeated_full_track_access_raises_abuse_flag(self):
        self.client.force_authenticate(self.fan)
        for _ in range(12):
            self.stream()

        self.assertTrue(
            MediaAbuseFlag.objects.filter(
                flag_type=MediaAbuseFlag.REPEATED_FULL_TRACK_ACCESS,
                user=self.fan,
            ).exists()
        )
        # Flags are deduplicated within the detection window.
        self.assertEqual(
            MediaAbuseFlag.objects.filter(
                flag_type=MediaAbuseFlag.REPEATED_FULL_TRACK_ACCESS,
                status=MediaAbuseFlag.OPEN,
            ).count(),
            1,
        )

    def test_normal_browser_stream_does_not_raise_bot_flag(self):
        self.client.force_authenticate(self.fan)
        self.stream()
        self.assertFalse(
            MediaAbuseFlag.objects.filter(flag_type=MediaAbuseFlag.BOT_LIKE_ACCESS).exists()
        )


class UploadHashTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="hash_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        ArtistProfile.objects.create(
            owner=self.artist,
            stage_name="Hash Artist",
            professions="music",
            is_verified=True,
        )

    def test_music_upload_stores_sha256_hash(self):
        self.client.force_authenticate(self.artist)
        response = self.client.post(
            "/api/media/create/",
            {
                "title": "Hashed Track",
                "audio_file": SimpleUploadedFile("hashed.mp3", b"hash-me"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)

        import hashlib

        track = MusicUpload.objects.get(title="Hashed Track")
        self.assertEqual(track.file_hash_sha256, hashlib.sha256(b"hash-me").hexdigest())
        self.assertTrue(track.is_master_private)
        self.assertEqual(track.ai_training_consent, AI_TRAINING_NOT_ALLOWED)

    def test_product_upload_stores_sha256_hash(self):
        self.client.force_authenticate(self.artist)
        response = self.client.post(
            "/api/marketplace/create/",
            {
                "title": "Hashed Pack",
                "product_type": Product.SAMPLE_PACK,
                "price": "5.00",
                "product_file": SimpleUploadedFile("hashed-pack.zip", b"zip-hash-me"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)

        import hashlib

        product = Product.objects.get(title="Hashed Pack")
        self.assertEqual(product.file_hash_sha256, hashlib.sha256(b"zip-hash-me").hexdigest())
