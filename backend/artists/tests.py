from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase

from artists.models import ArtistFanContact, ArtistFollow, ArtistProfessionProfile, ArtistProfile, FanJourneyEvent
from mediahub.models import MusicUpload
from subscriptions.models import FanSubscription, OneTimeTip, SupportTier


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
        self.assertTrue(
            FanJourneyEvent.objects.filter(
                fan=self.fan,
                artist=self.artist,
                event_type=FanJourneyEvent.FOLLOW,
            ).exists()
        )

    def test_artist_can_save_social_profile_links(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/artists/update-profile/",
            {
                "stage_name": "Artist",
                "instagram_url": "https://www.instagram.com/artist",
                "tiktok_url": "https://www.tiktok.com/@artist",
                "youtube_url": "https://www.youtube.com/@artist",
                "website_url": "https://artist.example.com",
                "website_label": "Official site",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.artist.artist_profile.refresh_from_db()
        self.assertEqual(self.artist.artist_profile.instagram_url, "https://www.instagram.com/artist")
        self.assertEqual(self.artist.artist_profile.tiktok_url, "https://www.tiktok.com/@artist")

    def test_artist_cannot_self_report_follower_counts(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/artists/update-profile/",
            {
                "stage_name": "Artist",
                "youtube_url": "https://www.youtube.com/@artist",
                "youtube_reach": "9000000 subscribers",
                "youtube_subscriber_count": 9000000,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.artist.artist_profile.refresh_from_db()
        # Reach is platform-verified only; without an API key it stays unset.
        self.assertIsNone(self.artist.artist_profile.youtube_subscriber_count)

        list_response = self.client.get("/api/artists/")
        artist_payload = next(item for item in list_response.data if item["owner_id"] == self.artist.id)
        self.assertEqual(artist_payload["youtube_reach"], "")
        self.assertFalse(artist_payload["youtube_reach_verified"])
        self.assertTrue(artist_payload["youtube_reach_pending"])

    def test_reach_hidden_when_no_youtube_url(self):
        profile = self.artist.artist_profile
        profile.youtube_url = ""
        profile.youtube_subscriber_count = 123456
        profile.save()

        self.assertFalse(profile.youtube_reach_verified())
        self.assertFalse(profile.youtube_reach_pending())
        self.assertEqual(profile.youtube_reach_display(), "")

        list_response = self.client.get("/api/artists/")
        artist_payload = next(item for item in list_response.data if item["owner_id"] == self.artist.id)
        self.assertFalse(artist_payload["youtube_reach_verified"])
        self.assertFalse(artist_payload["youtube_reach_pending"])
        self.assertEqual(artist_payload["youtube_reach"], "")

    def test_format_reach_renders_compact_counts(self):
        self.assertEqual(ArtistProfile.format_reach(950), "950")
        self.assertEqual(ArtistProfile.format_reach(12_300), "12.3K")
        self.assertEqual(ArtistProfile.format_reach(1_000_000), "1M")
        self.assertEqual(ArtistProfile.format_reach(2_400_000), "2.4M")
        self.assertEqual(ArtistProfile.format_reach(None), "")

    def test_artist_can_upload_cover_photo(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/artists/update-profile/",
            {
                "stage_name": "Artist",
                "hero_image": SimpleUploadedFile(
                    "cover.jpg",
                    b"fake-image-content",
                    content_type="image/jpeg",
                ),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.artist.artist_profile.refresh_from_db()
        self.assertTrue(self.artist.artist_profile.hero_image.name.startswith("artist_hero/"))
        self.assertIn("/media/artist_hero/", response.data["hero_image"])

    def test_artist_can_save_profession_specific_profile_details(self):
        self.artist.artist_profile.professions = "music,visual_art"
        self.artist.artist_profile.save(update_fields=["professions"])
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/artists/update-profile/",
            {
                "stage_name": "Artist",
                "professions": ["music", "visual_art"],
                "active_profession": "visual_art",
                "profession_display_title": "Artist Studio",
                "profession_tagline": "Watercolour originals and process notes",
                "profession_style": "Watercolour",
                "profession_bio": "Small works on paper from the studio.",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        profile = ArtistProfessionProfile.objects.get(
            artist_profile=self.artist.artist_profile,
            profession=ArtistProfile.VISUAL_ART,
        )
        self.assertEqual(profile.display_title, "Artist Studio")
        self.assertEqual(profile.style, "Watercolour")
        self.assertEqual(response.data["profession_profiles"]["visual_art"]["bio"], "Small works on paper from the studio.")

    def test_artist_can_upload_visitor_banner_for_profession(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/artists/update-profile/",
            {
                "stage_name": "Artist",
                "active_profession": ArtistProfile.MUSIC,
                "profession_visitor_banner": SimpleUploadedFile(
                    "welcome.mp4",
                    b"fake-video-content",
                    content_type="video/mp4",
                ),
                "profession_visitor_banner_duration": "45",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        profile = ArtistProfessionProfile.objects.get(
            artist_profile=self.artist.artist_profile,
            profession=ArtistProfile.MUSIC,
        )
        self.assertTrue(profile.visitor_banner.name.startswith("artist_visitor_banners/"))
        self.assertEqual(profile.visitor_banner_duration_seconds, 45)
        self.assertIn("/media/artist_visitor_banners/", response.data["profession_profiles"]["music"]["visitor_banner"])

        list_response = self.client.get("/api/artists/")
        artist_payload = next(item for item in list_response.data if item["owner_id"] == self.artist.id)
        self.assertEqual(artist_payload["profession_profiles"]["music"]["visitor_banner_duration_seconds"], 45)

    def test_artist_can_clear_visitor_banner(self):
        self.client.force_authenticate(self.artist)
        profile, _ = ArtistProfessionProfile.objects.get_or_create(
            artist_profile=self.artist.artist_profile,
            profession=ArtistProfile.MUSIC,
        )
        profile.visitor_banner = SimpleUploadedFile(
            "welcome.mp4",
            b"fake-video-content",
            content_type="video/mp4",
        )
        profile.save()

        response = self.client.post(
            "/api/artists/update-profile/",
            {
                "stage_name": "Artist",
                "active_profession": ArtistProfile.MUSIC,
                "profession_clear_visitor_banner": "true",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertFalse(profile.visitor_banner)
        self.assertIsNone(response.data["profession_profiles"]["music"]["visitor_banner"])

    def test_visitor_banner_rejects_invalid_file_type(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/artists/update-profile/",
            {
                "stage_name": "Artist",
                "active_profession": ArtistProfile.MUSIC,
                "profession_visitor_banner": SimpleUploadedFile(
                    "welcome.exe",
                    b"bad-content",
                    content_type="application/octet-stream",
                ),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Visitor banner", response.data["error"])

    def test_artist_page_builder_accepts_json_booleans(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/artists/update-page-builder/",
            {
                "show_music": True,
                "show_posts": False,
                "show_store": True,
                "show_lives": False,
                "show_about": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.artist.artist_profile.refresh_from_db()
        self.assertTrue(self.artist.artist_profile.show_music)
        self.assertFalse(self.artist.artist_profile.show_posts)
        self.assertTrue(self.artist.artist_profile.show_store)
        self.assertFalse(self.artist.artist_profile.show_lives)
        self.assertTrue(self.artist.artist_profile.show_about)

    def test_artist_page_builder_updates_themes(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/artists/update-page-builder/",
            {
                "theme_name": "theme-tribute-purple-rain",
                "studio_theme_name": "theme-boombap",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["theme_name"], "theme-tribute-purple-rain")
        self.assertEqual(response.data["studio_theme_name"], "theme-boombap")
        self.artist.artist_profile.refresh_from_db()
        self.assertEqual(self.artist.artist_profile.theme_name, "theme-tribute-purple-rain")
        self.assertEqual(self.artist.artist_profile.studio_theme_name, "theme-boombap")

    def test_artist_page_builder_rejects_invalid_theme(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/artists/update-page-builder/",
            {"theme_name": "theme-not-real"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.artist.artist_profile.refresh_from_db()
        self.assertEqual(self.artist.artist_profile.theme_name, "theme-indie-dark")

    def test_artist_page_builder_rejects_host_theme(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/artists/update-page-builder/",
            {"theme_name": "theme-host-velvet-lounge"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.artist.artist_profile.refresh_from_db()
        self.assertEqual(self.artist.artist_profile.theme_name, "theme-indie-dark")


class ArtistDashboardTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="dash_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        self.fan = User.objects.create_user(
            username="dash_fan",
            password="password123",
            email="fan@example.com",
            user_type=User.FAN,
            discovery_location="Melbourne",
        )
        self.second_fan = User.objects.create_user(
            username="second_fan",
            password="password123",
            email="second@example.com",
            user_type=User.FAN,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Dashboard Artist")

    def test_artist_dashboard_aggregates_business_health(self):
        tier = SupportTier.objects.create(
            artist=self.artist,
            name="Backstage",
            monthly_amount="5.00",
        )
        ArtistFollow.objects.create(fan=self.fan, artist=self.artist)
        ArtistFollow.objects.create(fan=self.second_fan, artist=self.artist)
        FanSubscription.objects.create(
            fan=self.fan,
            artist=self.artist,
            tier=tier,
            monthly_amount="5.00",
            active=True,
        )
        FanSubscription.objects.create(
            fan=self.second_fan,
            artist=self.artist,
            monthly_amount="2.00",
            active=True,
        )
        OneTimeTip.objects.create(
            fan=self.fan,
            artist=self.artist,
            amount="10.00",
            message="Keep going",
        )
        ArtistFanContact.objects.create(
            fan=self.fan,
            artist=self.artist,
            email_shared=True,
            shared_at=timezone.now(),
            source=ArtistFanContact.SUPPORT_PROMPT,
        )
        self.client.force_authenticate(self.artist)

        response = self.client.get("/api/artists/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["revenue"]["mrr"]["amount"], "7.00")
        self.assertEqual(response.data["revenue"]["tips_this_month"]["amount"], "10.00")
        self.assertEqual(response.data["revenue"]["total_revenue_this_month"]["amount"], "17.00")
        self.assertEqual(response.data["revenue"]["platform_fees_this_month"], "0.70")
        self.assertEqual(response.data["revenue"]["artist_share_this_month"], "16.30")
        self.assertEqual(response.data["fans"]["total_followers"], 2)
        self.assertEqual(response.data["fans"]["active_subscribers"], 2)
        self.assertEqual(response.data["fans"]["new_subscribers_7d"], 2)
        self.assertEqual(response.data["fans"]["new_subscribers_30d"], 2)
        self.assertEqual(response.data["fans"]["mailing_list_size"], 1)
        self.assertEqual(response.data["fans"]["mailing_list_growth_30d"], 1)
        self.assertEqual(response.data["ratios"]["supporter_to_follower_ratio"], 100)
        self.assertEqual(response.data["top_supporters"][0]["fan_username"], "dash_fan")
        self.assertEqual(response.data["top_supporters"][0]["total_spend"], "15.00")
        self.assertTrue(any(item["type"] == "follow" for item in response.data["recent_activity"]))
        self.assertTrue(any(item["type"] == "subscription" for item in response.data["recent_activity"]))

    def test_artist_dashboard_includes_funnel_and_track_conversions(self):
        track = MusicUpload.objects.create(
            artist=self.artist,
            title="Conversion Track",
            audio_file=SimpleUploadedFile("track.mp3", b"fake-audio", content_type="audio/mpeg"),
        )
        FanJourneyEvent.objects.create(
            fan=self.fan,
            artist=self.artist,
            event_type=FanJourneyEvent.PAGE_VIEW,
        )
        first_listen = FanJourneyEvent.objects.create(
            fan=self.fan,
            artist=self.artist,
            music_upload=track,
            event_type=FanJourneyEvent.MUSIC_PREVIEW,
        )
        FanJourneyEvent.objects.create(
            fan=self.fan,
            artist=self.artist,
            music_upload=track,
            event_type=FanJourneyEvent.MUSIC_FULL_PLAY,
        )
        FanJourneyEvent.objects.create(
            fan=self.fan,
            artist=self.artist,
            event_type=FanJourneyEvent.SUBSCRIBE,
            metadata={"referral_source": "instagram"},
        )
        self.client.force_authenticate(self.artist)

        response = self.client.get("/api/artists/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["funnel"]["visitors"], 1)
        self.assertEqual(response.data["funnel"]["event_counts"][FanJourneyEvent.MUSIC_PREVIEW], 1)
        track_payload = response.data["music_funnel"]["tracks"][0]
        self.assertEqual(track_payload["track_id"], track.id)
        self.assertEqual(track_payload["preview_plays"], 1)
        self.assertEqual(track_payload["full_plays"], 1)
        self.assertEqual(track_payload["subscriber_conversions_7d"], 1)
        self.assertEqual(response.data["referrals"]["supporters_this_month"][0]["source"], "instagram")
        self.assertEqual(response.data["referrals"]["supporters_this_month"][0]["supporters"], 1)

    def test_artist_dashboard_invite_funnel_conversion_rates(self):
        FanJourneyEvent.objects.create(
            fan=self.fan,
            artist=self.artist,
            event_type=FanJourneyEvent.FOLLOW,
            metadata={"referral_source": f"invite_{self.artist.username}"},
        )
        FanJourneyEvent.objects.create(
            fan=self.second_fan,
            artist=self.artist,
            event_type=FanJourneyEvent.FOLLOW,
            metadata={"referral_source": f"invite_{self.artist.username}"},
        )
        FanJourneyEvent.objects.create(
            fan=self.fan,
            artist=self.artist,
            event_type=FanJourneyEvent.SUBSCRIBE,
            metadata={"referral_source": f"invite_{self.artist.username}"},
        )
        FanJourneyEvent.objects.create(
            fan=self.second_fan,
            artist=self.artist,
            event_type=FanJourneyEvent.FOLLOW,
            metadata={"referral_source": "instagram"},
        )
        self.client.force_authenticate(self.artist)

        response = self.client.get("/api/artists/dashboard/")

        self.assertEqual(response.status_code, 200)
        referrals = response.data["referrals"]
        self.assertEqual(referrals["invite_link_follows"], 2)
        self.assertEqual(referrals["invite_link_subscribers"], 1)
        self.assertEqual(referrals["invite_follow_to_subscribe_rate"], 50.0)
        self.assertEqual(referrals["invite_follows"], 3)
        self.assertEqual(referrals["funnel"][0]["count"], 2)
        self.assertEqual(referrals["funnel"][1]["count"], 1)

    def test_artist_dashboard_requires_artist_account(self):
        self.client.force_authenticate(self.fan)

        response = self.client.get("/api/artists/dashboard/")

        self.assertEqual(response.status_code, 403)

    def test_artist_dashboard_exposes_fee_schedule(self):
        self.client.force_authenticate(self.artist)

        response = self.client.get("/api/artists/dashboard/")

        self.assertEqual(response.status_code, 200)
        schedule = response.data["fee_schedule"]
        items = {item["id"]: item for item in schedule["items"]}
        self.assertEqual(items["marketplace"]["you_keep_percent"], "85%")
        self.assertEqual(items["marketplace"]["platform_percent"], "15%")
        self.assertEqual(items["event_tickets"]["platform_percent"], "15%")
        self.assertEqual(items["event_tickets"]["you_keep_percent"], "85%")
        self.assertEqual(items["support"]["you_keep_percent"], "90%")
        self.assertEqual(items["tips"]["you_keep_percent"], "100%")
        self.assertEqual(items["commission"]["you_keep_percent"], "85%")
        self.assertIn("food & beverage", schedule["live_policy"])


class ArtistTrustAndProInsightsTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="trust_artist",
            password="password123",
            user_type=User.ARTIST,
            artist_plan="pro",
        )
        ArtistProfile.objects.create(
            owner=self.artist,
            stage_name="Trust Artist",
            city="Melbourne",
            artist_story="Independent human artist.",
        )

    def test_trust_status_flags_incomplete_profile(self):
        self.client.force_authenticate(self.artist)
        response = self.client.get("/api/artists/trust-status/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["profile_completion"]["complete"])
        self.assertIsNotNone(response.data["upload_limit_remaining"])

    def test_pro_insights_requires_pro_plan(self):
        self.artist.artist_plan = "free"
        self.artist.save(update_fields=["artist_plan"])
        self.client.force_authenticate(self.artist)
        response = self.client.get("/api/artists/pro-insights/")
        self.assertEqual(response.status_code, 403)

    def test_pro_insights_returns_segments_and_forecast(self):
        self.client.force_authenticate(self.artist)
        response = self.client.get("/api/artists/pro-insights/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("segments", response.data)
        self.assertIn("mrr_forecast", response.data)
        self.assertIn("local_gigs", response.data)
        self.assertEqual(response.data["local_gigs"]["city"], "Melbourne")

    def test_dashboard_includes_spaces_and_trust_summary(self):
        self.client.force_authenticate(self.artist)
        response = self.client.get("/api/artists/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("spaces", response.data)
        self.assertIn("trust", response.data)
        self.assertEqual(response.data["spaces"]["city"], "Melbourne")


class FansAlsoSupportTests(APITestCase):
    def setUp(self):
        self.fan_a = User.objects.create_user(username="fan_a", password="password123", user_type=User.FAN)
        self.fan_b = User.objects.create_user(username="fan_b", password="password123", user_type=User.FAN)
        self.artist = User.objects.create_user(username="main_artist", password="password123", user_type=User.ARTIST)
        self.similar = User.objects.create_user(username="similar_artist", password="password123", user_type=User.ARTIST)
        self.other = User.objects.create_user(username="other_artist", password="password123", user_type=User.ARTIST)
        ArtistProfile.objects.create(owner=self.artist, stage_name="Main", genre="hip-hop", city="Melbourne")
        ArtistProfile.objects.create(owner=self.similar, stage_name="Similar", genre="hip-hop", city="Melbourne")
        ArtistProfile.objects.create(owner=self.other, stage_name="Other", genre="jazz", city="Sydney")

        ArtistFollow.objects.create(fan=self.fan_a, artist=self.artist)
        ArtistFollow.objects.create(fan=self.fan_b, artist=self.artist)
        ArtistFollow.objects.create(fan=self.fan_a, artist=self.similar)
        FanSubscription.objects.create(
            fan=self.fan_b,
            artist=self.similar,
            monthly_amount="5.00",
            active=True,
        )

    def test_fans_also_support_returns_overlap_artists(self):
        response = self.client.get(f"/api/artists/fans-also-support/?artist_id={self.artist.id}")
        self.assertEqual(response.status_code, 200)
        usernames = [item["owner_username"] for item in response.data["results"]]
        self.assertIn("similar_artist", usernames)
        self.assertNotIn("main_artist", usernames)
        self.assertNotIn("other_artist", usernames)
