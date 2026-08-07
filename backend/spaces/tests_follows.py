from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from spaces.models import HostProfile, SpaceFollow, SpaceListing


User = get_user_model()


class SpaceFollowTests(APITestCase):
    def setUp(self):
        self.host = User.objects.create_user(username="host", password="password123", user_type=User.HOST)
        self.fan = User.objects.create_user(username="fan", password="password123", user_type=User.FAN)
        HostProfile.objects.create(user=self.host, business_name="North Room", city="Melbourne")
        self.listing = SpaceListing.objects.create(
            host=self.host,
            name="Back Room",
            description="Intimate stage for independent acts.",
            address="1 Test St",
            city="Melbourne",
            available_windows=[{"day": "fri", "start": "19:00", "end": "23:00"}],
            status=SpaceListing.LIVE,
        )
        self.draft = SpaceListing.objects.create(
            host=self.host,
            name="Draft Room",
            description="Not public yet.",
            address="2 Test St",
            city="Melbourne",
            available_windows=[{"day": "sat", "start": "19:00", "end": "23:00"}],
            status=SpaceListing.DRAFT,
        )

    def test_public_can_get_live_listing(self):
        response = self.client.get(f"/api/spaces/listings/{self.listing.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["listing"]["name"], "Back Room")
        self.assertEqual(response.data["listing"]["public_url"], f"/?listing={self.listing.id}")
        self.assertFalse(response.data["listing"]["viewer_following"])

    def test_draft_listing_is_hidden_from_public(self):
        response = self.client.get(f"/api/spaces/listings/{self.draft.id}/")
        self.assertEqual(response.status_code, 404)

    def test_fan_can_follow_and_unfollow_venue(self):
        self.client.force_authenticate(self.fan)
        follow = self.client.post(f"/api/spaces/listings/{self.listing.id}/follow/")
        self.assertEqual(follow.status_code, 200)
        self.assertTrue(follow.data["viewer_following"])
        self.assertTrue(SpaceFollow.objects.filter(fan=self.fan, listing=self.listing).exists())

        saved = self.client.get("/api/spaces/listings/followed/")
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.data["count"], 1)
        self.assertEqual(saved.data["results"][0]["id"], self.listing.id)

        unfollow = self.client.post(f"/api/spaces/listings/{self.listing.id}/unfollow/")
        self.assertEqual(unfollow.status_code, 200)
        self.assertFalse(SpaceFollow.objects.filter(fan=self.fan, listing=self.listing).exists())
