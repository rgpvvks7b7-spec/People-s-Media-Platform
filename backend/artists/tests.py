from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from artists.models import ArtistFollow, ArtistProfile


User = get_user_model()


class ArtistFollowTests(APITestCase):
    def setUp(self):
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
        self.artist = User.objects.create_user(
            username="artist",
            password="password123",
            user_type=User.ARTIST,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Artist")

    def test_fan_can_follow_artist_but_not_non_artist_user(self):
        self.client.force_authenticate(self.fan)

        artist_response = self.client.post(
            "/api/artists/follow/",
            {"artist_id": self.artist.id},
            format="json",
        )
        fan_response = self.client.post(
            "/api/artists/follow/",
            {"artist_id": self.other_fan.id},
            format="json",
        )

        self.assertEqual(artist_response.status_code, 200)
        self.assertEqual(fan_response.status_code, 400)
        self.assertTrue(ArtistFollow.objects.filter(fan=self.fan, artist=self.artist).exists())
        self.assertFalse(ArtistFollow.objects.filter(fan=self.fan, artist=self.other_fan).exists())
