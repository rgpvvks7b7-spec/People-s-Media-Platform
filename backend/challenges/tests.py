from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from artists.models import ArtistProfile
from challenges.models import ArtistChallengeProgress, ArtistStreak, ChallengeTemplate, GrowthPoints
from challenges.services import get_artist_challenge_board, increment_metric
from subscriptions.models import FanSubscription


User = get_user_model()


class ChallengeTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="challenge_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        self.fan = User.objects.create_user(
            username="challenge_fan",
            password="password123",
            user_type=User.FAN,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Challenge Artist")

    def test_today_endpoint_creates_daily_and_weekly_progress(self):
        self.client.force_authenticate(self.artist)

        response = self.client.get("/api/challenges/today/")

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data["daily"]), 3)
        self.assertGreaterEqual(len(response.data["weekly"]), 3)
        self.assertEqual(response.data["streak"]["current_streak"], 0)

    def test_progress_increments_on_real_instant_event_and_completes_daily_streak(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/posts/instants/",
            {"body": "Working on a chorus.", "visibility": "public"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        progress = ArtistChallengeProgress.objects.get(
            artist=self.artist,
            template__metric="post_instant",
            period_start=timezone.now().date(),
        )
        streak = ArtistStreak.objects.get(artist=self.artist)
        self.assertTrue(progress.completed_at)
        self.assertEqual(progress.progress, 1)
        self.assertEqual(streak.current_streak, 1)
        self.assertTrue(GrowthPoints.objects.filter(artist=self.artist, points=10).exists())

    def test_weekly_progress_increments_on_calendar_items(self):
        self.client.force_authenticate(self.artist)

        for index in range(2):
            response = self.client.post(
                "/api/artists/calendar/",
                {
                    "title": f"Public date {index}",
                    "starts_at": (timezone.now() + timezone.timedelta(days=index + 1)).isoformat(),
                    "visibility": "public",
                    "item_type": "gig",
                },
                format="json",
            )
            self.assertEqual(response.status_code, 201)

        progress = ArtistChallengeProgress.objects.get(
            artist=self.artist,
            template__metric="calendar_item",
            period_start=timezone.now().date() - timezone.timedelta(days=timezone.now().weekday()),
        )
        self.assertEqual(progress.progress, 2)
        self.assertTrue(progress.completed_at)
        self.assertTrue(GrowthPoints.objects.filter(artist=self.artist, points=30).exists())

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_new_subscriber_event_completes_weekly_challenge(self):
        self.client.force_authenticate(self.fan)

        response = self.client.post(
            "/api/subscriptions/subscribe/",
            {"artist_id": self.artist.id, "monthly_amount": "2.00", "billing_date": 1},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        progress = ArtistChallengeProgress.objects.get(artist=self.artist, template__metric="new_subscriber")
        self.assertTrue(progress.completed_at)

    def test_daily_period_rollover_creates_new_progress_without_resetting_old_record(self):
        yesterday = timezone.now() - timezone.timedelta(days=1)
        today = timezone.now()

        increment_metric(self.artist, "post_instant", now=yesterday)
        increment_metric(self.artist, "post_instant", now=today)

        rows = ArtistChallengeProgress.objects.filter(
            artist=self.artist,
            template__metric="post_instant",
        ).order_by("period_start")
        streak = ArtistStreak.objects.get(artist=self.artist)

        self.assertEqual(rows.count(), 2)
        self.assertTrue(all(row.completed_at for row in rows))
        self.assertEqual(streak.current_streak, 2)
        self.assertEqual(streak.longest_streak, 2)

    def test_claim_endpoint_can_increment_manual_metric(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post("/api/challenges/claim/", {"metric": "add_update_pov"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["completed_count"], 1)
        board = get_artist_challenge_board(self.artist)
        pov_item = next(item for item in board["daily"] if item["metric"] == "add_update_pov")
        self.assertTrue(pov_item["completed"])
