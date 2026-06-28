from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from artists.models import ArtistProfile
from campaigns.models import Campaign, CampaignMetrics
from campaigns.providers import (
    GoogleAdsProvider,
    MetaAdsProvider,
    SpotifyAdsProvider,
    TikTokAdsProvider,
    YouTubeAdsProvider,
    get_provider,
)

User = get_user_model()


class CampaignAccessTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="campaign_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        self.other_artist = User.objects.create_user(
            username="other_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        self.fan = User.objects.create_user(
            username="campaign_fan",
            password="password123",
            user_type=User.FAN,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Campaign Artist")
        ArtistProfile.objects.create(owner=self.other_artist, stage_name="Other Artist")

    def test_fan_cannot_list_campaigns(self):
        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/campaigns/")
        self.assertEqual(response.status_code, 403)

    def test_fan_cannot_create_campaign(self):
        self.client.force_authenticate(self.fan)
        response = self.client.post("/api/campaigns/", {"title": "Fan campaign"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_list_campaigns(self):
        response = self.client.get("/api/campaigns/")
        self.assertEqual(response.status_code, 401)


class CampaignCrudTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="growth_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        self.other_artist = User.objects.create_user(
            username="growth_other",
            password="password123",
            user_type=User.ARTIST,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Growth Artist")
        ArtistProfile.objects.create(owner=self.other_artist, stage_name="Growth Other")
        self.client.force_authenticate(self.artist)

    def test_create_list_update_delete_campaign(self):
        create_response = self.client.post(
            "/api/campaigns/",
            {
                "title": "Summer single push",
                "campaign_type": "new_song",
                "goal": "more_streams",
                "ad_networks": ["meta", "youtube"],
                "destination_type": "smart_link",
                "destination_url": "https://example.com/listen",
                "budget_daily": "10.00",
                "budget_total": "300.00",
                "duration_days": 30,
                "similar_artists": ["Artist One", "Artist Two"],
                "locations": ["United States", "Canada"],
                "age_min": 18,
                "age_max": 44,
                "creative_headline": "New song out now",
                "creative_text": "Tap listen and tell us what you think.",
                "status": "draft",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        campaign_id = create_response.data["campaign"]["id"]
        self.assertEqual(create_response.data["campaign"]["metrics"]["impressions"], 0)

        list_response = self.client.get("/api/campaigns/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data["results"]), 1)
        self.assertIn("metrics", list_response.data["results"][0])

        update_response = self.client.post(
            f"/api/campaigns/{campaign_id}/update/",
            {"title": "Updated title", "status": "ready"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data["campaign"]["title"], "Updated title")
        self.assertEqual(update_response.data["campaign"]["status"], "ready")

        delete_response = self.client.post(f"/api/campaigns/{campaign_id}/delete/")
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(Campaign.objects.filter(id=campaign_id).exists())

    def test_create_requires_title(self):
        response = self.client.post("/api/campaigns/", {"goal": "more_streams"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("title", response.data["error"])

    def test_cannot_access_other_artist_campaign(self):
        other_campaign = Campaign.objects.create(
            artist=self.other_artist,
            title="Other campaign",
            campaign_type=Campaign.NEW_SONG,
            goal=Campaign.MORE_STREAMS,
        )
        response = self.client.get(f"/api/campaigns/{other_campaign.id}/")
        self.assertEqual(response.status_code, 404)

    def test_multipart_create_with_creative(self):
        response = self.client.post(
            "/api/campaigns/",
            {
                "title": "Creative campaign",
                "campaign_type": "video",
                "goal": "video_views",
                "creative_file": SimpleUploadedFile("clip.mp4", b"video-bytes", content_type="video/mp4"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["campaign"]["creative_file_url"])

    def test_launched_campaign_returns_placeholder_metrics(self):
        campaign = Campaign.objects.create(
            artist=self.artist,
            title="Launched campaign",
            campaign_type=Campaign.NEW_SONG,
            goal=Campaign.MORE_STREAMS,
            status=Campaign.LAUNCHED,
            budget_daily=Decimal("10.00"),
            duration_days=30,
        )
        CampaignMetrics.objects.get_or_create(campaign=campaign)

        response = self.client.get(f"/api/campaigns/{campaign.id}/")
        self.assertEqual(response.status_code, 200)
        metrics = response.data["campaign"]["metrics"]
        self.assertTrue(metrics["placeholder"])
        self.assertGreater(metrics["impressions"], 0)
        self.assertGreater(metrics["clicks"], 0)


class ProviderRegistryTests(APITestCase):
    def test_provider_registry(self):
        self.assertIsInstance(get_provider("meta"), MetaAdsProvider)
        self.assertIsInstance(get_provider("google"), GoogleAdsProvider)
        self.assertIsInstance(get_provider("tiktok"), TikTokAdsProvider)
        self.assertIsInstance(get_provider("spotify"), SpotifyAdsProvider)
        self.assertIsInstance(get_provider("youtube"), YouTubeAdsProvider)
        self.assertIsNone(get_provider("unknown"))

    def test_meta_provider_validate_requires_destination(self):
        campaign = Campaign(
            title="Test",
            ad_networks=["meta"],
            destination_url="",
        )
        provider = MetaAdsProvider()
        errors = provider.validate_campaign(campaign)
        self.assertTrue(errors)

        campaign.destination_url = "https://example.com"
        errors = provider.validate_campaign(campaign)
        self.assertFalse(errors)

    def test_provider_launch_is_stub(self):
        campaign = Campaign(title="Test", ad_networks=["meta"])
        result = MetaAdsProvider().launch(campaign)
        self.assertEqual(result["integration"], "coming_soon")
        self.assertEqual(result["status"], "not_connected")
