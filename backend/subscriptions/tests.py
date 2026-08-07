from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from artists.models import ArtistFanContact, ArtistProfile, FanJourneyEvent
from subscriptions.models import FanSubscription, OneTimeTip, SupportTier
from subscriptions.views import activate_stripe_subscription


User = get_user_model()


@override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
class DemoSupportFallbackTests(APITestCase):
    def setUp(self):
        self.fan = User.objects.create_user(
            username="fan",
            password="password123",
            user_type=User.FAN,
        )
        self.artist = User.objects.create_user(
            username="artist",
            password="password123",
            user_type=User.ARTIST,
        )
        self.artist_two = User.objects.create_user(
            username="artist_two",
            password="password123",
            user_type=User.ARTIST,
        )
        self.other_fan = User.objects.create_user(
            username="other_fan",
            password="password123",
            user_type=User.FAN,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Artist", professions="music,visual_art")
        ArtistProfile.objects.create(owner=self.artist_two, stage_name="Artist Two")

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_checkout_creates_demo_subscription_without_stripe_keys(self):
        self.client.force_authenticate(self.fan)

        response = self.client.post(
            "/api/subscriptions/checkout/",
            {"artist_id": self.artist.id, "monthly_amount": "2.50"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["demo"])
        self.assertTrue(
            FanSubscription.objects.filter(
                fan=self.fan,
                artist=self.artist,
                profession="music",
                active=True,
                payment_provider="demo",
            ).exists()
        )
        self.assertTrue(
            FanJourneyEvent.objects.filter(
                fan=self.fan,
                artist=self.artist,
                event_type=FanJourneyEvent.SUBSCRIBE,
            ).exists()
        )
        from notifications.models import Notification

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.fan,
                notification_type=Notification.SUPPORTER,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.artist,
                notification_type=Notification.SUPPORTER,
            ).exists()
        )

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_checkout_with_global_email_opt_in_creates_artist_contact(self):
        self.fan.email = "fan@example.com"
        self.fan.share_email_with_supported_artists = True
        self.fan.save(update_fields=["email", "share_email_with_supported_artists"])
        self.client.force_authenticate(self.fan)

        response = self.client.post(
            "/api/subscriptions/checkout/",
            {"artist_id": self.artist.id, "monthly_amount": "2.50"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        contact = ArtistFanContact.objects.get(fan=self.fan, artist=self.artist)
        self.assertTrue(contact.email_shared)
        self.assertEqual(contact.source, ArtistFanContact.SIGNUP_OPT_IN)

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_checkout_without_consent_does_not_expose_email_to_artist(self):
        self.fan.email = "private@example.com"
        self.fan.save(update_fields=["email"])
        self.client.force_authenticate(self.fan)

        support_response = self.client.post(
            "/api/subscriptions/checkout/",
            {"artist_id": self.artist.id, "monthly_amount": "2.50"},
            format="json",
        )
        self.client.force_authenticate(self.artist)
        list_response = self.client.get("/api/artists/mailing-list/")

        self.assertEqual(support_response.status_code, 200)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 0)
        self.assertFalse(ArtistFanContact.objects.get(fan=self.fan, artist=self.artist).email_shared)

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_checkout_with_per_artist_prompt_creates_artist_contact(self):
        self.fan.email = "prompt@example.com"
        self.fan.save(update_fields=["email"])
        self.client.force_authenticate(self.fan)

        response = self.client.post(
            "/api/subscriptions/checkout/",
            {
                "artist_id": self.artist.id,
                "monthly_amount": "2.50",
                "share_email_with_artist": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        contact = ArtistFanContact.objects.get(fan=self.fan, artist=self.artist)
        self.assertTrue(contact.email_shared)
        self.assertEqual(contact.source, ArtistFanContact.SUPPORT_PROMPT)

    def test_artist_mailing_list_returns_only_consented_supporters(self):
        opted_in = User.objects.create_user(
            username="opted_in",
            password="password123",
            email="opted@example.com",
            user_type=User.FAN,
            discovery_location="Melbourne",
        )
        private = User.objects.create_user(
            username="private",
            password="password123",
            email="private@example.com",
            user_type=User.FAN,
        )
        FanSubscription.objects.create(fan=opted_in, artist=self.artist, monthly_amount="3.00")
        FanSubscription.objects.create(fan=private, artist=self.artist, monthly_amount="3.00")
        ArtistFanContact.objects.create(
            fan=opted_in,
            artist=self.artist,
            email_shared=True,
            source=ArtistFanContact.SUPPORT_PROMPT,
        )
        ArtistFanContact.objects.create(
            fan=private,
            artist=self.artist,
            email_shared=False,
            source=ArtistFanContact.MANUAL,
        )
        self.client.force_authenticate(self.artist)

        response = self.client.get("/api/artists/mailing-list/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["email"], "opted@example.com")
        self.assertEqual(response.data["results"][0]["location"], "Melbourne")

    def test_mailing_list_csv_requires_artist_pro(self):
        self.client.force_authenticate(self.artist)

        free_response = self.client.get("/api/artists/mailing-list/?export=csv")
        self.artist.artist_plan = "pro"
        self.artist.save(update_fields=["artist_plan"])
        pro_response = self.client.get("/api/artists/mailing-list/?export=csv")

        self.assertEqual(free_response.status_code, 403)
        self.assertEqual(pro_response.status_code, 200)
        self.assertEqual(pro_response["Content-Type"], "text/csv")

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_checkout_support_is_separate_per_profession(self):
        self.client.force_authenticate(self.fan)

        music_response = self.client.post(
            "/api/subscriptions/checkout/",
            {"artist_id": self.artist.id, "profession": "music", "monthly_amount": "1.00"},
            format="json",
        )
        art_response = self.client.post(
            "/api/subscriptions/checkout/",
            {"artist_id": self.artist.id, "profession": "visual_art", "monthly_amount": "1.00"},
            format="json",
        )

        self.assertEqual(music_response.status_code, 200)
        self.assertEqual(art_response.status_code, 200)
        self.assertEqual(
            FanSubscription.objects.filter(fan=self.fan, artist=self.artist, active=True).count(),
            2,
        )
        self.assertTrue(FanSubscription.objects.filter(fan=self.fan, artist=self.artist, profession="music").exists())
        self.assertTrue(FanSubscription.objects.filter(fan=self.fan, artist=self.artist, profession="visual_art").exists())

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_fan_can_support_new_phase_five_profession(self):
        self.artist.artist_profile.professions = "music,podcast"
        self.artist.artist_profile.save(update_fields=["professions"])
        self.client.force_authenticate(self.fan)

        response = self.client.post(
            "/api/subscriptions/checkout/",
            {"artist_id": self.artist.id, "profession": "podcast", "monthly_amount": "3.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        sub = FanSubscription.objects.get(fan=self.fan, artist=self.artist, profession="podcast")
        self.assertEqual(str(sub.monthly_amount), "3.00")
        self.assertEqual(response.data["profession_label"], "Podcaster")

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_artist_can_create_tier_and_fan_can_support_it(self):
        self.client.force_authenticate(self.artist)
        tier_response = self.client.post(
            "/api/subscriptions/tiers/",
            {
                "profession": "visual_art",
                "name": "Collector",
                "monthly_amount": "5.00",
                "benefits": "Early access to prints",
            },
            format="json",
        )

        tier = SupportTier.objects.get(name="Collector")
        self.client.force_authenticate(self.fan)
        support_response = self.client.post(
            "/api/subscriptions/checkout/",
            {"artist_id": self.artist.id, "profession": "visual_art", "tier_id": tier.id},
            format="json",
        )

        self.assertEqual(tier_response.status_code, 201)
        self.assertEqual(support_response.status_code, 200)
        sub = FanSubscription.objects.get(fan=self.fan, artist=self.artist, profession="visual_art")
        self.assertEqual(sub.tier, tier)
        self.assertEqual(str(sub.monthly_amount), "5.00")
        self.assertEqual(str(sub.artist_share), "4.50")
        self.assertEqual(support_response.data["tier_name"], "Collector")

    def test_stripe_activation_preserves_support_tier(self):
        tier = SupportTier.objects.create(
            artist=self.artist,
            profession="visual_art",
            name="Collector",
            monthly_amount="5.00",
        )

        activate_stripe_subscription({
            "id": "cs_test_123",
            "customer": "cus_123",
            "subscription": "sub_123",
            "payment_status": "paid",
            "metadata": {
                "fan_id": str(self.fan.id),
                "artist_id": str(self.artist.id),
                "profession": "visual_art",
                "tier_id": str(tier.id),
                "monthly_amount": "5.00",
            },
        })

        sub = FanSubscription.objects.get(fan=self.fan, artist=self.artist, profession="visual_art")
        self.assertEqual(sub.tier, tier)
        self.assertEqual(str(sub.monthly_amount), "5.00")
        self.assertEqual(sub.payment_provider, "stripe")

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_checkout_rejects_profession_artist_does_not_offer(self):
        self.client.force_authenticate(self.fan)

        response = self.client.post(
            "/api/subscriptions/checkout/",
            {"artist_id": self.artist_two.id, "profession": "visual_art", "monthly_amount": "1.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Artist does not offer this profession")

    def test_subscription_list_is_empty_for_anonymous_users(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, monthly_amount="2.00")

        response = self.client.get("/api/subscriptions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["subscriptions"], [])
        self.assertEqual(response.data["fan_totals"], {})
        self.assertEqual(response.data["artist_totals"], {})

    def test_fan_subscription_list_only_returns_their_own_supports(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, monthly_amount="2.00")
        FanSubscription.objects.create(fan=self.other_fan, artist=self.artist_two, monthly_amount="4.00")
        self.client.force_authenticate(self.fan)

        response = self.client.get("/api/subscriptions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["subscriptions"]), 1)
        self.assertEqual(response.data["subscriptions"][0]["fan"], "fan")
        self.assertEqual(response.data["fan_totals"], {"fan": "2.00"})
        self.assertEqual(response.data["artist_totals"], {"artist": "1.80"})

    def test_artist_subscription_list_only_returns_their_supporters(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, monthly_amount="2.00")
        FanSubscription.objects.create(fan=self.other_fan, artist=self.artist_two, monthly_amount="4.00")
        self.client.force_authenticate(self.artist)

        response = self.client.get("/api/subscriptions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["subscriptions"]), 1)
        self.assertEqual(response.data["subscriptions"][0]["artist"], "artist")
        self.assertEqual(response.data["fan_totals"], {"fan": "2.00"})
        self.assertEqual(response.data["artist_totals"], {"artist": "1.80"})

    def test_checkout_rejects_non_artist_target_and_invalid_amount(self):
        self.client.force_authenticate(self.fan)

        non_artist_response = self.client.post(
            "/api/subscriptions/checkout/",
            {"artist_id": self.other_fan.id, "monthly_amount": "2.00"},
            format="json",
        )
        invalid_amount_response = self.client.post(
            "/api/subscriptions/checkout/",
            {"artist_id": self.artist.id, "monthly_amount": "not-money"},
            format="json",
        )

        self.assertEqual(non_artist_response.status_code, 400)
        self.assertEqual(invalid_amount_response.status_code, 400)
        self.assertFalse(FanSubscription.objects.filter(fan=self.fan, artist=self.other_fan).exists())

    def test_direct_subscribe_validates_artist_amount_and_billing_date(self):
        self.client.force_authenticate(self.fan)

        bad_artist_response = self.client.post(
            "/api/subscriptions/subscribe/",
            {"artist_id": self.other_fan.id, "monthly_amount": "2.00", "billing_date": 1},
            format="json",
        )
        bad_amount_response = self.client.post(
            "/api/subscriptions/subscribe/",
            {"artist_id": self.artist.id, "monthly_amount": "abc", "billing_date": 1},
            format="json",
        )
        bad_billing_date_response = self.client.post(
            "/api/subscriptions/subscribe/",
            {"artist_id": self.artist.id, "monthly_amount": "2.00", "billing_date": 32},
            format="json",
        )

        self.assertEqual(bad_artist_response.status_code, 400)
        self.assertEqual(bad_amount_response.status_code, 400)
        self.assertEqual(bad_billing_date_response.status_code, 400)
        self.assertFalse(FanSubscription.objects.filter(fan=self.fan, artist=self.artist).exists())

    def test_direct_subscribe_records_referral_source(self):
        self.client.force_authenticate(self.fan)

        response = self.client.post(
            "/api/subscriptions/subscribe/",
            {
                "artist_id": self.artist.id,
                "monthly_amount": "2.00",
                "billing_date": 1,
                "referral_source": "instagram",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        event = FanJourneyEvent.objects.get(
            fan=self.fan,
            artist=self.artist,
            event_type=FanJourneyEvent.SUBSCRIBE,
        )
        self.assertEqual(event.metadata["referral_source"], "instagram")

    def test_fan_can_send_one_time_tip_with_public_message(self):
        self.client.force_authenticate(self.fan)

        response = self.client.post(
            "/api/subscriptions/tips/",
            {
                "artist_id": self.artist.id,
                "profession": "visual_art",
                "amount": "5.00",
                "message": "This print series is beautiful.",
                "is_public": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        tip = OneTimeTip.objects.get(fan=self.fan, artist=self.artist, profession="visual_art")
        self.assertEqual(str(tip.amount), "5.00")
        self.assertEqual(str(tip.artist_share), "5.00")
        self.assertEqual(tip.message, "This print series is beautiful.")

        list_response = self.client.get(
            f"/api/subscriptions/tips/?artist_id={self.artist.id}&profession=visual_art"
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["results"][0]["message"], "This print series is beautiful.")

    def test_tip_rejects_self_and_unoffered_profession(self):
        self.client.force_authenticate(self.artist)
        self_response = self.client.post(
            "/api/subscriptions/tips/",
            {"artist_id": self.artist.id, "profession": "music", "amount": "5.00"},
            format="json",
        )

        self.client.force_authenticate(self.fan)
        profession_response = self.client.post(
            "/api/subscriptions/tips/",
            {"artist_id": self.artist_two.id, "profession": "visual_art", "amount": "5.00"},
            format="json",
        )

        self.assertEqual(self_response.status_code, 400)
        self.assertEqual(profession_response.status_code, 400)

    def test_anonymous_tip_list_requires_artist_id(self):
        response = self.client.get("/api/subscriptions/tips/")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "artist_id is required")
