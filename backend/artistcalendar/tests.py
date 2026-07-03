from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from artists.models import ArtistProfile
from artistcalendar.models import ArtistCalendarItem
from subscriptions.models import FanSubscription


User = get_user_model()


class ArtistCalendarTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="calendar_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        self.fan = User.objects.create_user(
            username="calendar_fan",
            password="password123",
            user_type=User.FAN,
        )
        self.supporter = User.objects.create_user(
            username="calendar_supporter",
            password="password123",
            user_type=User.FAN,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Calendar Artist")

    def test_artist_can_create_private_calendar_item_hidden_from_fans(self):
        self.client.force_authenticate(self.artist)
        response = self.client.post(
            "/api/artists/calendar/",
            {
                "title": "Private release planning",
                "starts_at": (timezone.now() + timezone.timedelta(days=10)).isoformat(),
                "item_type": ArtistCalendarItem.RELEASE,
                "visibility": ArtistCalendarItem.PRIVATE,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        artist_response = self.client.get("/api/artists/calendar/")
        self.client.force_authenticate(self.fan)
        fan_response = self.client.get(f"/api/artists/calendar/?artist_id={self.artist.id}")

        self.assertEqual(artist_response.data["count"], 1)
        self.assertEqual(fan_response.data["count"], 0)

    def test_public_release_date_shows_on_artist_profile(self):
        item = ArtistCalendarItem.objects.create(
            artist=self.artist,
            title="Single release",
            starts_at=timezone.now() + timezone.timedelta(days=3),
            item_type=ArtistCalendarItem.RELEASE,
            visibility=ArtistCalendarItem.PUBLIC,
        )

        response = self.client.get("/api/artists/")
        artist_payload = next(row for row in response.data if row["owner_id"] == self.artist.id)

        self.assertEqual(artist_payload["upcoming_calendar_items"][0]["id"], item.id)
        self.assertEqual(artist_payload["upcoming_calendar_items"][0]["title"], "Single release")

    def test_supporter_early_access_hides_public_item_until_window_for_non_supporters(self):
        ArtistCalendarItem.objects.create(
            artist=self.artist,
            title="Secret gig reveal",
            starts_at=timezone.now() + timezone.timedelta(days=10),
            item_type=ArtistCalendarItem.GIG,
            visibility=ArtistCalendarItem.PUBLIC,
            supporter_early_hours=24 * 14,
        )

        self.client.force_authenticate(self.fan)
        fan_response = self.client.get(f"/api/artists/calendar/?artist_id={self.artist.id}")

        FanSubscription.objects.create(fan=self.supporter, artist=self.artist, active=True)
        self.client.force_authenticate(self.supporter)
        supporter_response = self.client.get(f"/api/artists/calendar/?artist_id={self.artist.id}")

        self.assertEqual(fan_response.data["count"], 0)
        self.assertEqual(supporter_response.data["count"], 1)
        self.assertEqual(supporter_response.data["results"][0]["title"], "Secret gig reveal")

    def test_supporter_only_calendar_item_requires_support(self):
        ArtistCalendarItem.objects.create(
            artist=self.artist,
            title="Supporter listening party",
            starts_at=timezone.now() + timezone.timedelta(days=2),
            item_type=ArtistCalendarItem.LIVE,
            visibility=ArtistCalendarItem.SUPPORTERS,
        )

        self.client.force_authenticate(self.fan)
        fan_response = self.client.get(f"/api/artists/calendar/?artist_id={self.artist.id}")

        FanSubscription.objects.create(fan=self.supporter, artist=self.artist, active=True)
        self.client.force_authenticate(self.supporter)
        supporter_response = self.client.get(f"/api/artists/calendar/?artist_id={self.artist.id}")

        self.assertEqual(fan_response.data["count"], 0)
        self.assertEqual(supporter_response.data["count"], 1)

    def test_calendar_feed_returns_public_items(self):
        ArtistCalendarItem.objects.create(
            artist=self.artist,
            title="Public show",
            starts_at=timezone.now() + timezone.timedelta(days=2),
            item_type=ArtistCalendarItem.GIG,
            visibility=ArtistCalendarItem.PUBLIC,
        )

        response = self.client.get(f"/api/artists/calendar/feed.ics?artist_id={self.artist.id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn("BEGIN:VCALENDAR", response.content.decode())
        self.assertIn("Public show", response.content.decode())
