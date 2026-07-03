from django.test import TestCase

from accounts.models import User
from spaces.models import HostProfile, SpaceListing, SpaceListingPhoto
from spaces.placeholder_photos import build_space_photo_jpeg, ensure_listing_gallery


class SpacePlaceholderPhotoTests(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username="photo_host", password="pass", user_type=User.HOST)
        HostProfile.objects.create(user=self.host, business_name="Photo Venue", city="Melbourne")
        self.listing = SpaceListing.objects.create(
            host=self.host,
            name="Laneway Stage",
            city="Melbourne",
            status=SpaceListing.LIVE,
        )

    def test_build_space_photo_jpeg_returns_valid_image(self):
        payload = build_space_photo_jpeg(self.listing, SpaceListingPhoto.STAGE, "Stage view")
        self.assertTrue(payload.startswith(b"\xff\xd8"))
        self.assertGreater(len(payload), 1000)

    def test_ensure_listing_gallery_creates_stage_bar_and_room_photos(self):
        created = ensure_listing_gallery(self.listing)
        self.assertEqual(created, 3)
        types = list(self.listing.gallery_photos.values_list("photo_type", flat=True))
        self.assertIn(SpaceListingPhoto.STAGE, types)
        self.assertIn(SpaceListingPhoto.AUDIENCE, types)
        self.assertIn(SpaceListingPhoto.ROOM_OVERVIEW, types)

    def test_ensure_listing_gallery_is_idempotent(self):
        ensure_listing_gallery(self.listing)
        self.assertEqual(self.listing.gallery_photos.count(), 3)
        ensure_listing_gallery(self.listing)
        self.assertEqual(self.listing.gallery_photos.count(), 3)
