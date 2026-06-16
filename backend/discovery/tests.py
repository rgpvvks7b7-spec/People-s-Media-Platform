from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from artists.models import ArtistFollow, ArtistProfile
from discovery.models import ArtistSignal
from mediahub.models import MusicUpload
from posts.models import Post
from subscriptions.models import FanSubscription


User = get_user_model()


class ArtistRecommendationTests(APITestCase):
    def setUp(self):
        self.fan = User.objects.create_user(
            username="fan",
            password="password123",
            user_type=User.FAN,
            favorite_genres="indie pop, bedroom pop",
            discovery_location="Melbourne",
        )
        self.luna = User.objects.create_user(
            username="luna",
            password="password123",
            user_type=User.ARTIST,
        )
        self.static = User.objects.create_user(
            username="static",
            password="password123",
            user_type=User.ARTIST,
        )
        self.noise = User.objects.create_user(
            username="noise",
            password="password123",
            user_type=User.ARTIST,
        )

        ArtistProfile.objects.create(
            owner=self.luna,
            stage_name="Luna Lane",
            genre="Indie Pop",
            city="Melbourne",
            artist_story="Warm synths, late-night vocals and diary hooks.",
            influences="Clairo, BENEE",
            is_verified=True,
        )
        ArtistProfile.objects.create(
            owner=self.static,
            stage_name="Static Harbor",
            genre="Alt R&B",
            city="Sydney",
            artist_story="Dusty keys and patient choruses.",
            influences="Steve Lacy, SZA",
        )
        ArtistProfile.objects.create(
            owner=self.noise,
            stage_name="Noise Room",
            genre="Noise",
            city="Perth",
            artist_story="Heavy feedback studies.",
            influences="Experimental",
        )

        MusicUpload.objects.create(
            artist=self.luna,
            title="Paper Moons",
            audio_file="music/paper-moons.mp3",
            genre="Indie Pop",
        )
        Post.objects.create(author=self.luna, title="Update", body="New demo soon.")
        ArtistFollow.objects.create(fan=self.fan, artist=self.luna)
        FanSubscription.objects.create(fan=self.fan, artist=self.luna, monthly_amount="2.00")

    def test_anonymous_recommendations_include_scores_and_reasons(self):
        response = self.client.get("/api/discovery/artists/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertFalse(response.data["personalized"])
        self.assertEqual(response.data["results"][0]["owner_username"], "luna")
        self.assertIn("discovery_score", response.data["results"][0])
        self.assertGreater(len(response.data["results"][0]["discovery_reasons"]), 0)

    def test_authenticated_fan_gets_personalized_genre_and_location_boosts(self):
        self.client.force_authenticate(self.fan)

        response = self.client.get("/api/discovery/artists/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["personalized"])
        top_result = response.data["results"][0]
        reason_labels = [reason["label"] for reason in top_result["discovery_reasons"]]

        self.assertEqual(top_result["owner_username"], "luna")
        self.assertTrue(any("Matches your taste" in label for label in reason_labels))
        self.assertTrue(any("Near Melbourne" in label for label in reason_labels))
        self.assertTrue(top_result["viewer_following"])
        self.assertTrue(all("category" in reason for reason in top_result["discovery_reasons"]))
        self.assertTrue(all("detail" in reason for reason in top_result["discovery_reasons"]))

    def test_artist_does_not_get_their_own_profile_recommended(self):
        self.client.force_authenticate(self.luna)

        response = self.client.get("/api/discovery/artists/")
        usernames = [artist["owner_username"] for artist in response.data["results"]]

        self.assertNotIn("luna", usernames)

    def test_query_and_location_filters_apply_before_scoring(self):
        response = self.client.get("/api/discovery/artists/?q=static&location=Sydney")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["owner_username"], "static")

    def test_backfill_returns_broader_artists_when_filter_is_exhausted(self):
        ArtistSignal.objects.create(
            fan=self.fan,
            artist=self.luna,
            signal_type=ArtistSignal.SKIP,
            liked_genre="Indie Pop",
            weight=-1,
        )
        self.client.force_authenticate(self.fan)

        response = self.client.get("/api/discovery/artists/?location=Melbourne&backfill=true")
        usernames = [artist["owner_username"] for artist in response.data["results"]]

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("luna", usernames)
        self.assertIn("static", usernames)
        self.assertTrue(response.data["results"][0]["relaxed_match"])

    def test_authenticated_fan_can_save_discovery_signal(self):
        self.client.force_authenticate(self.fan)

        response = self.client.post(
            "/api/discovery/signal/",
            {"artist_id": self.static.id, "signal_type": ArtistSignal.SAVE},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            ArtistSignal.objects.filter(
                fan=self.fan,
                artist=self.static,
                signal_type=ArtistSignal.SAVE,
            ).exists()
        )

    def test_skip_signal_hides_artist_from_recommendations(self):
        ArtistSignal.objects.create(
            fan=self.fan,
            artist=self.static,
            signal_type=ArtistSignal.SKIP,
            liked_genre="Alt R&B",
            weight=-1,
        )
        self.client.force_authenticate(self.fan)

        response = self.client.get("/api/discovery/artists/")
        usernames = [artist["owner_username"] for artist in response.data["results"]]

        self.assertNotIn("static", usernames)

    def test_more_like_this_signal_adds_similarity_reason(self):
        ArtistSignal.objects.create(
            fan=self.fan,
            artist=self.static,
            signal_type=ArtistSignal.MORE_LIKE_THIS,
            liked_genre="Alt R&B",
            weight=1.2,
        )
        cousin = User.objects.create_user(
            username="static_cousin",
            password="password123",
            user_type=User.ARTIST,
        )
        ArtistProfile.objects.create(
            owner=cousin,
            stage_name="Static Cousin",
            genre="Alt R&B",
            city="Adelaide",
            artist_story="Dusty keys and slow drums.",
            influences="Steve Lacy",
        )
        self.client.force_authenticate(self.fan)

        response = self.client.get("/api/discovery/artists/?q=cousin")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        reason_labels = [reason["label"] for reason in response.data["results"][0]["discovery_reasons"]]
        self.assertIn("Similar to artists you follow or support", reason_labels)

    def test_saved_artists_returns_saved_profiles_for_authenticated_fan(self):
        ArtistSignal.objects.create(
            fan=self.fan,
            artist=self.static,
            signal_type=ArtistSignal.SAVE,
            liked_genre="Alt R&B",
            weight=1.4,
        )
        self.client.force_authenticate(self.fan)

        response = self.client.get("/api/discovery/saved-artists/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["authenticated"])
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["owner_username"], "static")
        self.assertEqual(response.data["results"][0]["viewer_signal"], ArtistSignal.SAVE)

    def test_authenticated_fan_can_remove_saved_artist(self):
        ArtistSignal.objects.create(
            fan=self.fan,
            artist=self.static,
            signal_type=ArtistSignal.SAVE,
            liked_genre="Alt R&B",
            weight=1.4,
        )
        self.client.force_authenticate(self.fan)

        response = self.client.post(
            "/api/discovery/remove-saved/",
            {"artist_id": self.static.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["deleted_count"], 1)
        self.assertFalse(
            ArtistSignal.objects.filter(
                fan=self.fan,
                artist=self.static,
                signal_type=ArtistSignal.SAVE,
            ).exists()
        )

    def test_authenticated_fan_can_undo_specific_signal(self):
        ArtistSignal.objects.create(
            fan=self.fan,
            artist=self.static,
            signal_type=ArtistSignal.MORE_LIKE_THIS,
            liked_genre="Alt R&B",
            weight=1.2,
        )
        self.client.force_authenticate(self.fan)

        response = self.client.post(
            "/api/discovery/undo-signal/",
            {"artist_id": self.static.id, "signal_type": ArtistSignal.MORE_LIKE_THIS},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["deleted_count"], 1)
        self.assertFalse(
            ArtistSignal.objects.filter(
                fan=self.fan,
                artist=self.static,
                signal_type=ArtistSignal.MORE_LIKE_THIS,
            ).exists()
        )

    def test_saved_artists_returns_empty_list_for_anonymous_user(self):
        response = self.client.get("/api/discovery/saved-artists/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["authenticated"])
        self.assertEqual(response.data["results"], [])

    def test_authenticated_fan_can_reset_skipped_artists(self):
        ArtistSignal.objects.create(
            fan=self.fan,
            artist=self.static,
            signal_type=ArtistSignal.SKIP,
            liked_genre="Alt R&B",
            weight=-1,
        )
        self.client.force_authenticate(self.fan)

        response = self.client.post("/api/discovery/reset-skips/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["deleted_count"], 1)
        self.assertFalse(
            ArtistSignal.objects.filter(
                fan=self.fan,
                signal_type=ArtistSignal.SKIP,
            ).exists()
        )

    def test_authenticated_fan_can_undo_one_skipped_artist(self):
        ArtistSignal.objects.create(
            fan=self.fan,
            artist=self.static,
            signal_type=ArtistSignal.SKIP,
            liked_genre="Alt R&B",
            weight=-1,
        )
        ArtistSignal.objects.create(
            fan=self.fan,
            artist=self.noise,
            signal_type=ArtistSignal.SKIP,
            liked_genre="Noise",
            weight=-1,
        )
        self.client.force_authenticate(self.fan)

        response = self.client.post(
            "/api/discovery/undo-skip/",
            {"artist_id": self.static.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["deleted_count"], 1)
        self.assertFalse(
            ArtistSignal.objects.filter(
                fan=self.fan,
                artist=self.static,
                signal_type=ArtistSignal.SKIP,
            ).exists()
        )
        self.assertTrue(
            ArtistSignal.objects.filter(
                fan=self.fan,
                artist=self.noise,
                signal_type=ArtistSignal.SKIP,
            ).exists()
        )
