import hashlib

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from artists.models import ArtistFanContact, ArtistProfile
from marketplace.models import Product
from mediahub.models import MusicUpload
from notifications.models import Notification
from originlock.models import PasskeyCredential, ReleaseApproval
from originlock.services import compute_file_sha256, is_publicly_released

User = get_user_model()

AUDIO_BYTES = b"origin-lock-audio-bytes"


class ReleaseApprovalUploadTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="sealer",
            password="password123",
            user_type=User.ARTIST,
        )
        self.fan = User.objects.create_user(
            username="listener",
            password="password123",
            user_type=User.FAN,
        )
        self.profile = ArtistProfile.objects.create(
            owner=self.artist,
            stage_name="Sealer",
            professions="music",
            is_verified=True,
        )
        ArtistFanContact.objects.create(
            fan=self.fan,
            artist=self.artist,
            email_shared=True,
            source=ArtistFanContact.SUPPORT_PROMPT,
        )

    def upload_track(self, title="Sealed Song", **extra):
        self.client.force_authenticate(self.artist)
        payload = {
            "title": title,
            "audio_file": SimpleUploadedFile(f"{title}.mp3", AUDIO_BYTES, content_type="audio/mpeg"),
        }
        payload.update(extra)
        response = self.client.post("/api/media/create/", payload, format="multipart")
        self.assertEqual(response.status_code, 201)
        return response.data

    def test_upload_creates_pending_approval_with_sha256_hash(self):
        data = self.upload_track()

        approval = ReleaseApproval.objects.get(id=data["release_approval_id"])
        self.assertEqual(approval.approval_status, ReleaseApproval.PENDING)
        self.assertEqual(approval.file_hash, hashlib.sha256(AUDIO_BYTES).hexdigest())
        self.assertEqual(approval.artist, self.artist)

    def test_upload_does_not_notify_supporters_until_sealed(self):
        self.upload_track()
        self.assertFalse(
            Notification.objects.filter(recipient=self.fan, notification_type=Notification.MUSIC).exists()
        )

    def test_pending_track_hidden_from_public_but_visible_to_owner(self):
        data = self.upload_track()
        track_id = data["id"]

        self.client.logout()
        public = self.client.get("/api/media/")
        self.assertNotIn(track_id, {track["id"] for track in public.data})

        self.client.force_authenticate(self.artist)
        owner = self.client.get("/api/media/")
        owner_track = next(track for track in owner.data if track["id"] == track_id)
        self.assertEqual(owner_track["release_status"], ReleaseApproval.PENDING)
        self.assertEqual(owner_track["origin_badges"], [])

    def test_unverified_artist_cannot_seal(self):
        data = self.upload_track()
        self.profile.is_verified = False
        self.profile.save(update_fields=["is_verified"])

        self.client.force_authenticate(self.artist)
        response = self.client.post(
            f"/api/originlock/releases/{data['release_approval_id']}/seal/",
            {"approval_method": "password_fallback", "password": "password123"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        approval = ReleaseApproval.objects.get(id=data["release_approval_id"])
        self.assertEqual(approval.approval_status, ReleaseApproval.PENDING)

    def test_password_fallback_seal_publishes_and_notifies(self):
        data = self.upload_track(is_subscriber_only="false")
        track_id = data["id"]

        self.client.force_authenticate(self.artist)
        response = self.client.post(
            f"/api/originlock/releases/{data['release_approval_id']}/seal/",
            {
                "approval_method": "password_fallback",
                "password": "password123",
                "rights_owner": "Sealer",
                "ai_training_consent": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        approval = ReleaseApproval.objects.get(id=data["release_approval_id"])
        self.assertEqual(approval.approval_status, ReleaseApproval.APPROVED)
        self.assertEqual(approval.approval_method, ReleaseApproval.PASSWORD_FALLBACK)
        self.assertTrue(approval.ai_training_consent)

        self.assertTrue(
            Notification.objects.filter(recipient=self.fan, notification_type=Notification.MUSIC).exists()
        )

        self.client.logout()
        public = self.client.get("/api/media/")
        payload = next(track for track in public.data if track["id"] == track_id)
        self.assertEqual(payload["release_status"], ReleaseApproval.APPROVED)
        self.assertIn("Origin Locked", payload["origin_badges"])
        self.assertIn("Do Not Train", payload["origin_badges"])
        self.assertIn(f"/api/media/tracks/{track_id}/stream/", payload["audio_file"])
        self.assertNotIn("/media/music/", payload["audio_file"])

    def test_wrong_password_does_not_seal(self):
        data = self.upload_track()
        self.client.force_authenticate(self.artist)
        response = self.client.post(
            f"/api/originlock/releases/{data['release_approval_id']}/seal/",
            {"approval_method": "password_fallback", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_passkey_seal_marks_human_verified(self):
        data = self.upload_track()
        self.client.force_authenticate(self.artist)

        begin = self.client.post("/api/originlock/passkeys/register/begin/", {}, format="json")
        self.client.post(
            "/api/originlock/passkeys/register/complete/",
            {
                "challenge": begin.data["challenge"],
                "credential_id": "cred-abc-123",
                "public_key": "fake-public-key",
                "label": "MacBook",
            },
            format="json",
        )
        self.assertTrue(PasskeyCredential.objects.filter(credential_id="cred-abc-123").exists())

        auth_begin = self.client.post("/api/originlock/passkeys/authenticate/begin/", {}, format="json")
        response = self.client.post(
            f"/api/originlock/releases/{data['release_approval_id']}/seal/",
            {
                "approval_method": "passkey",
                "passkey": {
                    "challenge": auth_begin.data["challenge"],
                    "credential_id": "cred-abc-123",
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        approval = ReleaseApproval.objects.get(id=data["release_approval_id"])
        self.assertEqual(approval.approval_method, ReleaseApproval.PASSKEY)
        self.assertIn("Human Verified", response.data["origin_lock"]["badges"])

    def test_hash_mismatch_on_seal_is_rejected(self):
        data = self.upload_track()
        approval = ReleaseApproval.objects.get(id=data["release_approval_id"])
        approval.file_hash = "0" * 64
        approval.save(update_fields=["file_hash"])

        self.client.force_authenticate(self.artist)
        response = self.client.post(
            f"/api/originlock/releases/{data['release_approval_id']}/seal/",
            {"approval_method": "password_fallback", "password": "password123"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)


class OriginLockHelperTests(APITestCase):
    def test_objects_without_approval_are_treated_as_released(self):
        artist = User.objects.create_user(username="legacy", password="pw", user_type=User.ARTIST)
        ArtistProfile.objects.create(owner=artist, stage_name="Legacy", professions="music")
        track = MusicUpload.objects.create(
            artist=artist,
            title="Legacy Track",
            audio_file="music/legacy.mp3",
        )
        self.assertTrue(is_publicly_released(track))

    def test_compute_file_sha256_matches_hashlib(self):
        upload = SimpleUploadedFile("clip.mp3", AUDIO_BYTES)
        self.assertEqual(compute_file_sha256(upload), hashlib.sha256(AUDIO_BYTES).hexdigest())


class ProductReleaseApprovalTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="beatmaker",
            password="password123",
            user_type=User.ARTIST,
        )
        self.profile = ArtistProfile.objects.create(
            owner=self.artist,
            stage_name="Beatmaker",
            professions="music",
            is_verified=True,
        )

    def test_digital_product_requires_sealing_before_public(self):
        self.client.force_authenticate(self.artist)
        response = self.client.post(
            "/api/marketplace/create/",
            {
                "title": "Sample Pack",
                "product_type": Product.SAMPLE_PACK,
                "price": "5.00",
                "product_file": SimpleUploadedFile("pack.zip", b"zip-bytes"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("release_approval_id", response.data)
        product_id = response.data["id"]

        self.client.logout()
        public = self.client.get("/api/marketplace/")
        self.assertNotIn(product_id, {product["id"] for product in public.data})

        self.client.force_authenticate(self.artist)
        seal = self.client.post(
            f"/api/originlock/releases/{response.data['release_approval_id']}/seal/",
            {"approval_method": "password_fallback", "password": "password123"},
            format="json",
        )
        self.assertEqual(seal.status_code, 200)

        self.client.logout()
        public = self.client.get("/api/marketplace/")
        payload = next(product for product in public.data if product["id"] == product_id)
        self.assertIn("Origin Locked", payload["origin_badges"])
        # Paid download copies stay purchase-gated even after sealing.
        self.assertIsNone(payload["product_file"])
        self.assertFalse(payload["can_download"])

        self.client.force_authenticate(self.artist)
        owner = self.client.get("/api/marketplace/")
        owner_payload = next(product for product in owner.data if product["id"] == product_id)
        self.assertIn(f"/api/marketplace/files/{product_id}/download/", owner_payload["product_file"])

    def test_non_file_product_stays_immediate(self):
        self.client.force_authenticate(self.artist)
        response = self.client.post(
            "/api/marketplace/create/",
            {"title": "Sticker", "product_type": Product.MERCH, "price": "3.00"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("release_approval_id", response.data)
        product_id = response.data["id"]

        self.client.logout()
        public = self.client.get("/api/marketplace/")
        self.assertIn(product_id, {product["id"] for product in public.data})
