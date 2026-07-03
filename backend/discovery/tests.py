from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from artists.models import ArtistProfile
from artists.business_health import get_artist_business_health
from artists.models import ArtistFollow
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
            professions="film",
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

    def test_profession_filter_applies_before_scoring(self):
        response = self.client.get("/api/discovery/artists/?profession=film")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["owner_username"], "static")
        self.assertEqual(response.data["results"][0]["profession_keys"], ["film"])

    def test_invalid_profession_filter_is_rejected(self):
        response = self.client.get("/api/discovery/artists/?profession=not-real")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Invalid profession")

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

    def test_save_signal_hides_artist_from_recommendations(self):
        ArtistSignal.objects.create(
            fan=self.fan,
            artist=self.static,
            signal_type=ArtistSignal.SAVE,
            liked_genre="Alt R&B",
            weight=1.4,
        )
        self.client.force_authenticate(self.fan)

        response = self.client.get("/api/discovery/artists/?backfill=true")
        usernames = [artist["owner_username"] for artist in response.data["results"]]

        self.assertNotIn("static", usernames)
        saved_response = self.client.get("/api/discovery/saved-artists/")
        self.assertEqual(saved_response.data["count"], 1)

    def test_playlist_saved_track_hides_artist_from_recommendations(self):
        from mediahub.models import FanPlaylist, FanPlaylistTrack

        track = MusicUpload.objects.create(
            artist=self.static,
            title="Harbor Demo",
            audio_file="music/harbor-demo.mp3",
            genre="Alt R&B",
        )
        playlist = FanPlaylist.objects.create(owner=self.fan, title="Late Night")
        FanPlaylistTrack.objects.create(playlist=playlist, track=track)
        self.client.force_authenticate(self.fan)

        response = self.client.get("/api/discovery/artists/?backfill=true")
        usernames = [artist["owner_username"] for artist in response.data["results"]]

        self.assertNotIn("static", usernames)

    def test_recommendations_include_preview_track_payload(self):
        response = self.client.get("/api/discovery/artists/?q=luna")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["preview_track"]["title"], "Paper Moons")

    def test_track_recommendations_return_playable_tracks(self):
        response = self.client.get("/api/discovery/tracks/?q=paper")

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Paper Moons")
        self.assertIn("artist", response.data["results"][0])

    def test_saved_track_hidden_from_track_recommendations(self):
        from mediahub.models import FanPlaylist, FanPlaylistTrack

        track = MusicUpload.objects.get(title="Paper Moons")
        playlist = FanPlaylist.objects.create(owner=self.fan, title="Favorites")
        FanPlaylistTrack.objects.create(playlist=playlist, track=track)
        self.client.force_authenticate(self.fan)

        response = self.client.get("/api/discovery/tracks/?backfill=true")
        titles = [item["title"] for item in response.data["results"]]

        self.assertNotIn("Paper Moons", titles)

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
        self.assertIn("Similar to artists you support or saved", reason_labels)

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

    def test_business_health_handles_zero_followers_without_division_error(self):
        profile = self.static.artist_profile

        health = get_artist_business_health(self.static, profile)

        self.assertEqual(health["followers"], 0)
        self.assertEqual(health["supporter_ratio"], 0)

    def test_supporter_ratio_can_surface_one_hundred_percent_supporters(self):
        ArtistFollow.objects.create(fan=self.fan, artist=self.static)
        FanSubscription.objects.create(fan=self.fan, artist=self.static, monthly_amount="3.00", active=True)

        response = self.client.get("/api/discovery/artists/?q=static")

        self.assertEqual(response.status_code, 200)
        result = response.data["results"][0]
        self.assertEqual(result["business_health"]["followers"], 1)
        self.assertEqual(result["business_health"]["active_subscribers"], 1)
        self.assertEqual(result["business_health"]["monthly_artist_share"], "2.70")
        self.assertEqual(result["business_health"]["supporter_ratio"], 100)
        self.assertEqual(result["signals"]["supporter_ratio"], 100)

    def test_inactive_hiatus_artist_gets_non_punitive_hiatus_badge(self):
        profile = self.static.artist_profile
        profile.on_hiatus = True
        profile.save(update_fields=["on_hiatus"])

        response = self.client.get("/api/discovery/artists/?q=static")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["business_health"]["engagement"]["badge"], "On hiatus")

    def test_emerging_lane_includes_new_or_low_follower_artists(self):
        response = self.client.get("/api/discovery/artists/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("emerging", response.data)
        self.assertTrue(any(item["business_health"]["is_emerging"] for item in response.data["emerging"]))

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

    def test_fallback_surfaces_artists_when_fan_saved_everyone(self):
        for artist in (self.luna, self.static, self.noise):
            ArtistSignal.objects.update_or_create(
                fan=self.fan,
                artist=artist,
                signal_type=ArtistSignal.SAVE,
                defaults={"liked_genre": "demo", "weight": 1.0},
            )

        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/discovery/artists/?backfill=true")

        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data["count"], 0)
        self.assertFalse(response.data["exhausted"])
        self.assertTrue(any(item.get("already_saved") for item in response.data["results"]))


class PlayingNearYouTests(APITestCase):
    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone
        from spaces.models import HostProfile, SpaceBooking, SpaceListing

        self.fan = User.objects.create_user(
            username="local_fan",
            password="password123",
            user_type=User.FAN,
            discovery_location="Melbourne",
        )
        self.host = User.objects.create_user(username="venue_host", password="password123", user_type=User.HOST)
        self.artist = User.objects.create_user(username="gig_artist", password="password123", user_type=User.ARTIST)
        ArtistProfile.objects.create(owner=self.artist, stage_name="Gig Artist", city="Melbourne", genre="indie")
        HostProfile.objects.create(user=self.host, business_name="Late Room Bar", city="Melbourne")
        listing = SpaceListing.objects.create(
            host=self.host,
            name="Back Room",
            city="Melbourne",
            status=SpaceListing.LIVE,
            bar_open=True,
        )
        starts_at = timezone.now() + timedelta(days=4)
        SpaceBooking.objects.create(
            listing=listing,
            artist=self.artist,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=2),
            status=SpaceBooking.CONFIRMED,
        )

    def test_playing_near_you_returns_local_confirmed_gigs(self):
        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/discovery/playing-near-you/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["stage_name"], "Gig Artist")
        self.assertEqual(response.data["results"][0]["venue_name"], "Back Room")

    def test_my_scene_splits_all_and_supported_shows(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, active=True, monthly_amount="3.00")
        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/discovery/my-scene/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["counts"]["all"], 1)
        self.assertEqual(response.data["counts"]["supported"], 1)
        self.assertTrue(response.data["supported_shows"][0]["is_supported"])

    def test_my_scene_includes_ticket_when_linked(self):
        from marketplace.models import Product
        from spaces.models import SpaceBooking

        ticket = Product.objects.create(
            artist=self.artist,
            title="Door cover",
            product_type=Product.EVENT_TICKET,
            price="12.00",
            is_active=True,
        )
        booking = SpaceBooking.objects.get(artist=self.artist)
        booking.ticket_product = ticket
        booking.save(update_fields=["ticket_product"])

        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/discovery/my-scene/")
        self.assertEqual(response.status_code, 200)
        show = response.data["all_shows"][0]
        self.assertEqual(show["ticket"]["id"], ticket.id)
        self.assertEqual(show["ticket"]["price"], "12.00")

    def test_show_detail_returns_ticket_and_pitch(self):
        from spaces.models import SpaceBooking

        booking = SpaceBooking.objects.get(artist=self.artist)
        self.client.force_authenticate(self.fan)
        response = self.client.get(f"/api/discovery/shows/{booking.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["show"]["booking_id"], booking.id)
        self.assertEqual(response.data["show"]["venue_name"], "Back Room")
        self.assertFalse(response.data["show"]["has_ended"])

    def test_show_detail_serves_completed_show_with_ended_flag(self):
        from datetime import timedelta

        from django.utils import timezone

        from spaces.models import SpaceBooking

        booking = SpaceBooking.objects.get(artist=self.artist)
        booking.status = SpaceBooking.COMPLETED
        booking.starts_at = timezone.now() - timedelta(days=2)
        booking.ends_at = booking.starts_at + timedelta(hours=2)
        booking.save(update_fields=["status", "starts_at", "ends_at"])

        self.client.force_authenticate(self.fan)
        response = self.client.get(f"/api/discovery/shows/{booking.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["show"]["booking_id"], booking.id)
        self.assertEqual(response.data["show"]["status"], SpaceBooking.COMPLETED)
        self.assertTrue(response.data["show"]["has_ended"])
        self.assertFalse(response.data["show"].get("can_check_in", False))

    def test_show_detail_404_for_cancelled_show(self):
        from spaces.models import SpaceBooking

        booking = SpaceBooking.objects.get(artist=self.artist)
        booking.status = SpaceBooking.CANCELLED
        booking.save(update_fields=["status"])

        self.client.force_authenticate(self.fan)
        response = self.client.get(f"/api/discovery/shows/{booking.id}/")
        self.assertEqual(response.status_code, 404)

    def test_saved_artists_include_next_local_gig(self):
        from discovery.models import ArtistSignal

        ArtistSignal.objects.create(
            fan=self.fan,
            artist=self.artist,
            signal_type=ArtistSignal.SAVE,
            liked_genre="indie",
        )
        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/discovery/saved-artists/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        gig = response.data["results"][0]["next_local_gig"]
        self.assertIsNotNone(gig)
        self.assertEqual(gig["venue_name"], "Back Room")

    def test_recommendations_include_next_local_gig(self):
        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/discovery/artists/?location=melbourne")
        self.assertEqual(response.status_code, 200)
        artist = next(item for item in response.data["results"] if item["owner_username"] == "gig_artist")
        self.assertIsNotNone(artist["next_local_gig"])
        self.assertEqual(artist["next_local_gig"]["venue_name"], "Back Room")
