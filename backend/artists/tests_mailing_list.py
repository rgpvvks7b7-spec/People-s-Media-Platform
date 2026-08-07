from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from artists.models import ArtistFanContact, ArtistProfile
from subscriptions.models import FanSubscription, OneTimeTip, SupportTier


User = get_user_model()


@override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
class MailingListStudioTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="list_artist",
            password="password123",
            user_type=User.ARTIST,
            artist_plan="free",
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="List Artist", city="Melbourne")
        self.fan = User.objects.create_user(
            username="list_fan",
            password="password123",
            user_type=User.FAN,
            email="list_fan@example.com",
            discovery_location="Melbourne",
        )
        self.tip_fan = User.objects.create_user(
            username="tip_fan",
            password="password123",
            user_type=User.FAN,
            email="tip_fan@example.com",
            discovery_location="Sydney",
        )
        contact = ArtistFanContact.objects.create(fan=self.fan, artist=self.artist)
        contact.share(source=ArtistFanContact.SUPPORT_PROMPT)
        contact.save()
        tip_contact = ArtistFanContact.objects.create(fan=self.tip_fan, artist=self.artist)
        tip_contact.share(source=ArtistFanContact.SIGNUP_OPT_IN)
        tip_contact.save()
        tier = SupportTier.objects.create(artist=self.artist, name="Backstage", monthly_amount="5.00")
        FanSubscription.objects.create(
            fan=self.fan,
            artist=self.artist,
            tier=tier,
            monthly_amount="5.00",
            active=True,
        )
        OneTimeTip.objects.create(fan=self.tip_fan, artist=self.artist, amount="3.00", message="Nice")

    def test_free_artist_sees_masked_emails_and_export_nudge_threshold(self):
        for index in range(8):
            fan = User.objects.create_user(
                username=f"bulk_fan_{index}",
                password="password123",
                user_type=User.FAN,
                email=f"bulk{index}@example.com",
            )
            contact = ArtistFanContact.objects.create(fan=fan, artist=self.artist)
            contact.share(source=ArtistFanContact.MANUAL)
            contact.save()

        self.client.force_authenticate(self.artist)
        response = self.client.get("/api/artists/mailing-list/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 10)
        self.assertTrue(response.data["export_nudge"])
        self.assertFalse(response.data["can_export"])
        self.assertIn("*", response.data["results"][0]["email"])
        self.assertEqual(response.data["source_mix"]["manual"], 8)
        self.assertTrue(response.data["template_context"]["profile_city_set"])
        self.assertEqual(response.data["template_context"]["city"], "Melbourne")

    def test_filters_supporters_and_tips(self):
        self.client.force_authenticate(self.artist)

        supporters = self.client.get("/api/artists/mailing-list/?filter=supporters")
        tips = self.client.get("/api/artists/mailing-list/?filter=tips")

        self.assertEqual(supporters.status_code, 200)
        self.assertEqual(supporters.data["filtered_count"], 1)
        self.assertEqual(supporters.data["results"][0]["fan_username"], "list_fan")

        self.assertEqual(tips.status_code, 200)
        self.assertEqual(tips.data["filtered_count"], 1)
        self.assertEqual(tips.data["results"][0]["fan_username"], "tip_fan")

    def test_pro_artist_can_export_csv(self):
        self.artist.artist_plan = "pro"
        self.artist.save(update_fields=["artist_plan"])
        self.client.force_authenticate(self.artist)

        response = self.client.get("/api/artists/mailing-list/?export=csv")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        body = response.content.decode()
        self.assertIn("list_fan@example.com", body)
        self.assertIn("tip_fan@example.com", body)
