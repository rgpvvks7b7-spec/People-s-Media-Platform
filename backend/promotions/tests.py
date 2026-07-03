from decimal import Decimal

from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from artists.models import ArtistFollow, ArtistProfile
from mediahub.models import MusicUpload

from config.platform_fees import (
    CAMPAIGN_MAX_BUDGET,
    DISCOVERY_ADS_TAGLINE,
    FAN_DISCOVERY_REWARD,
    FAN_DISCOVERY_REWARD_DAILY_CAP,
)

from .models import Campaign, CampaignEvent, PromotionLedgerEntry
from .services import (
    campaigns_for_fan,
    charge_engagement,
    compute_discovery_score,
    fan_rewards_today,
    grant_credits,
    promotion_invariants,
    record_ledger_entry,
    refund_campaign_escrow,
    try_fund_campaign,
    wallet_balance,
)

User = get_user_model()


class PromotionTestBase(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="artist", password="pw", user_type=User.ARTIST,
        )
        self.profile = ArtistProfile.objects.create(
            owner=self.artist, stage_name="Boom Artist", genre="hip-hop boom-bap", city="Melbourne",
        )
        self.fan = User.objects.create_user(
            username="fan", password="pw", user_type=User.FAN,
            favorite_genres="hip-hop", discovery_location="Melbourne",
        )
        self.track = MusicUpload.objects.create(
            artist=self.artist, title="Promo Track", audio_file="music/promo.mp3", genre="hip-hop",
        )

    def make_active_campaign(self, **kwargs):
        defaults = dict(
            artist=self.artist,
            target_type=Campaign.TRACK,
            target_id=self.track.id,
            budget=Decimal("50.00"),
            status=Campaign.ACTIVE,
            target_genres="hip-hop",
            activated_at=timezone.now(),
        )
        defaults.update(kwargs)
        return Campaign.objects.create(**defaults)


class BudgetCapTests(PromotionTestBase):
    def test_budget_capped_at_max_in_model(self):
        campaign = Campaign.objects.create(
            artist=self.artist, target_type=Campaign.TRACK, target_id=self.track.id,
            budget=Decimal("5000.00"),
        )
        self.assertEqual(campaign.budget, Decimal("100.00"))

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_create_campaign_rejects_over_cap(self):
        grant_credits(self.artist, Decimal("100.00"))
        self.client.force_authenticate(self.artist)
        response = self.client.post(
            "/api/promotions/campaigns/",
            {"target_type": "track", "target_id": self.track.id, "budget": "250"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("capped", response.data["error"])

    def test_cannot_exceed_max_active_campaigns(self):
        for _ in range(4):
            self.make_active_campaign()
        ok, reason = Campaign.can_launch(self.artist)
        self.assertFalse(ok)
        self.assertIn("active campaigns", reason)

    def test_cooldown_blocks_new_launch(self):
        Campaign.objects.create(
            artist=self.artist, target_type=Campaign.TRACK, target_id=self.track.id,
            status=Campaign.COMPLETED, cooldown_until=timezone.now() + timezone.timedelta(days=2),
        )
        ok, reason = Campaign.can_launch(self.artist)
        self.assertFalse(ok)
        self.assertIn("cooldown", reason)


class WalletTests(PromotionTestBase):
    def test_ledger_tracks_running_balance(self):
        grant_credits(self.artist, Decimal("30.00"))
        grant_credits(self.artist, Decimal("20.00"))
        self.assertEqual(wallet_balance(self.artist), Decimal("50.00"))
        last = PromotionLedgerEntry.objects.filter(user=self.artist).first()
        self.assertEqual(last.balance_after, Decimal("50.00"))

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_create_campaign_funds_from_wallet(self):
        grant_credits(self.artist, Decimal("60.00"))
        self.client.force_authenticate(self.artist)
        response = self.client.post(
            "/api/promotions/campaigns/",
            {"target_type": "track", "target_id": self.track.id, "budget": "50", "target_genres": "hip-hop"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["funded_from"], "wallet")
        self.assertEqual(wallet_balance(self.artist), Decimal("10.00"))
        campaign = Campaign.objects.get(id=response.data["campaign"]["id"])
        self.assertEqual(campaign.status, Campaign.ACTIVE)

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_create_campaign_needs_credits_when_short(self):
        self.client.force_authenticate(self.artist)
        response = self.client.post(
            "/api/promotions/campaigns/",
            {"target_type": "track", "target_id": self.track.id, "budget": "50"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["needs_credits"])
        campaign = Campaign.objects.get(id=response.data["campaign"]["id"])
        self.assertEqual(campaign.status, Campaign.DRAFT)


class DraftLaunchTests(PromotionTestBase):
    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_credits_auto_launch_draft_campaign(self):
        self.client.force_authenticate(self.artist)
        create = self.client.post(
            "/api/promotions/campaigns/",
            {"target_type": "track", "target_id": self.track.id, "budget": "50", "target_genres": "hip-hop"},
            format="json",
        )
        self.assertTrue(create.data["needs_credits"])
        campaign = Campaign.objects.get(id=create.data["campaign"]["id"])
        self.assertEqual(campaign.status, Campaign.DRAFT)

        buy = self.client.post("/api/promotions/credits/checkout/", {"amount": "50"}, format="json")
        self.assertEqual(buy.status_code, 200)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, Campaign.ACTIVE)

    def test_launch_action_funds_draft(self):
        from promotions.models import PromotionLedgerEntry
        from promotions.services import record_ledger_entry

        campaign = Campaign.objects.create(
            artist=self.artist,
            target_type=Campaign.TRACK,
            target_id=self.track.id,
            budget=Decimal("25.00"),
            status=Campaign.DRAFT,
            target_genres="hip-hop",
        )
        record_ledger_entry(
            self.artist,
            PromotionLedgerEntry.PURCHASE,
            Decimal("25.00"),
            description="Manual test top-up",
        )
        self.client.force_authenticate(self.artist)
        response = self.client.post(
            f"/api/promotions/campaigns/{campaign.id}/action/",
            {"action": "launch"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, Campaign.ACTIVE)


class EscrowBillingTests(PromotionTestBase):
    def test_engagement_does_not_double_debit_wallet(self):
        grant_credits(self.artist, Decimal("50.00"))
        campaign = Campaign.objects.create(
            artist=self.artist,
            target_type=Campaign.TRACK,
            target_id=self.track.id,
            budget=Decimal("50.00"),
            status=Campaign.DRAFT,
            target_genres="hip-hop",
            title="Escrow test",
        )
        self.assertTrue(try_fund_campaign(campaign, self.artist)[0])
        self.assertEqual(wallet_balance(self.artist), Decimal("0.00"))

        charge_engagement(Campaign.TRACK, self.track.id, self.fan, "save")
        campaign.refresh_from_db()
        self.assertEqual(campaign.spent, Decimal("0.25"))
        self.assertEqual(wallet_balance(self.artist), Decimal("0.00"))

        refund_campaign_escrow(campaign, self.artist)
        self.assertEqual(wallet_balance(self.artist), Decimal("49.75"))

    def test_cancel_action_refunds_unused_escrow(self):
        grant_credits(self.artist, Decimal("50.00"))
        campaign = Campaign.objects.create(
            artist=self.artist,
            target_type=Campaign.TRACK,
            target_id=self.track.id,
            budget=Decimal("50.00"),
            status=Campaign.DRAFT,
            target_genres="hip-hop",
        )
        try_fund_campaign(campaign, self.artist)
        charge_engagement(Campaign.TRACK, self.track.id, self.fan, "follow")
        campaign.refresh_from_db()
        self.assertEqual(campaign.spent, Decimal("0.50"))

        self.client.force_authenticate(self.artist)
        response = self.client.post(
            f"/api/promotions/campaigns/{campaign.id}/action/",
            {"action": "cancel"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(wallet_balance(self.artist), Decimal("49.50"))

    def test_wallet_debits_equal_escrow_minus_refunds(self):
        grant_credits(self.artist, Decimal("100.00"))
        campaign = Campaign.objects.create(
            artist=self.artist,
            target_type=Campaign.TRACK,
            target_id=self.track.id,
            budget=Decimal("50.00"),
            status=Campaign.DRAFT,
            target_genres="hip-hop",
        )
        try_fund_campaign(campaign, self.artist)
        charge_engagement(Campaign.TRACK, self.track.id, self.fan, "save")
        charge_engagement(Campaign.TRACK, self.track.id, self.fan, "follow")
        campaign.refresh_from_db()
        refund_campaign_escrow(campaign, self.artist)

        spent_entries = PromotionLedgerEntry.objects.filter(
            user=self.artist, entry_type=PromotionLedgerEntry.SPEND
        ).aggregate(total=Sum("amount"))["total"]
        refund_entries = PromotionLedgerEntry.objects.filter(
            user=self.artist, entry_type=PromotionLedgerEntry.REFUND
        ).aggregate(total=Sum("amount"))["total"]
        net = (spent_entries or Decimal("0")) + (refund_entries or Decimal("0"))
        self.assertEqual(net, -campaign.spent)
        self.assertEqual(wallet_balance(self.artist), Decimal("100.00") - campaign.spent)


class EngagementBillingTests(PromotionTestBase):
    def test_full_listen_charges_once_per_fan(self):
        campaign = self.make_active_campaign()
        grant_credits(self.artist, Decimal("50.00"))
        charge_engagement(Campaign.TRACK, self.track.id, self.fan, "full_listen")
        charge_engagement(Campaign.TRACK, self.track.id, self.fan, "full_listen")
        campaign.refresh_from_db()
        self.assertEqual(campaign.spent, Decimal("0.15"))
        self.assertEqual(
            CampaignEvent.objects.filter(campaign=campaign, event_type="full_listen").count(), 1
        )

    def test_engagement_not_charged_when_budget_exhausted(self):
        campaign = self.make_active_campaign(budget=Decimal("5.00"), spent=Decimal("5.00"))
        charge_engagement(Campaign.TRACK, self.track.id, self.fan, "follow")
        campaign.refresh_from_db()
        self.assertEqual(campaign.spent, Decimal("5.00"))

    def test_fan_earns_reward_credit_on_engagement(self):
        self.make_active_campaign()
        charge_engagement(Campaign.TRACK, self.track.id, self.fan, "save")
        self.assertEqual(wallet_balance(self.fan), FAN_DISCOVERY_REWARD)
        last = PromotionLedgerEntry.objects.filter(user=self.fan).first()
        self.assertEqual(last.entry_type, PromotionLedgerEntry.REWARD)

    def test_fan_reward_once_per_campaign(self):
        self.make_active_campaign()
        charge_engagement(Campaign.TRACK, self.track.id, self.fan, "save")
        charge_engagement(Campaign.TRACK, self.track.id, self.fan, "follow")
        self.assertEqual(wallet_balance(self.fan), FAN_DISCOVERY_REWARD)

    def test_fan_reward_respects_daily_cap(self):
        self.make_active_campaign(budget=Decimal("100.00"))
        for i in range(25):
            other = User.objects.create_user(
                username=f"other{i}", password="pw", user_type=User.ARTIST,
            )
            ArtistProfile.objects.create(owner=other, stage_name=f"Other {i}", genre="hip-hop")
            track = MusicUpload.objects.create(
                artist=other, title=f"Track {i}", audio_file=f"music/t{i}.mp3", genre="hip-hop",
            )
            Campaign.objects.create(
                artist=other,
                target_type=Campaign.TRACK,
                target_id=track.id,
                budget=Decimal("50.00"),
                status=Campaign.ACTIVE,
                target_genres="hip-hop",
                activated_at=timezone.now(),
            )
            charge_engagement(Campaign.TRACK, track.id, self.fan, "save")
        self.assertLessEqual(fan_rewards_today(self.fan), FAN_DISCOVERY_REWARD_DAILY_CAP)

    def test_share_bills_and_rewards_once(self):
        campaign = self.make_active_campaign()
        charge_engagement(Campaign.TRACK, self.track.id, self.fan, "share")
        charge_engagement(Campaign.TRACK, self.track.id, self.fan, "share")
        campaign.refresh_from_db()
        self.assertEqual(campaign.spent, Decimal("0.20"))
        self.assertEqual(wallet_balance(self.fan), FAN_DISCOVERY_REWARD)

    def test_share_endpoint_records_engagement(self):
        self.make_active_campaign()
        self.client.force_authenticate(self.fan)
        response = self.client.post(
            "/api/promotions/share/",
            {"campaign_id": Campaign.objects.first().id},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["charged_campaigns"], 1)
        self.assertEqual(response.data["wallet_balance"], str(FAN_DISCOVERY_REWARD))

    def test_feedback_up_bills_campaign_and_rewards_fan(self):
        grant_credits(self.artist, Decimal("50.00"))
        campaign = Campaign.objects.create(
            artist=self.artist,
            target_type=Campaign.TRACK,
            target_id=self.track.id,
            budget=Decimal("50.00"),
            status=Campaign.DRAFT,
            target_genres="hip-hop",
        )
        try_fund_campaign(campaign, self.artist)
        self.client.force_authenticate(self.fan)
        response = self.client.post(
            "/api/promotions/feedback/",
            {"campaign_id": campaign.id, "verdict": "up"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        campaign.refresh_from_db()
        self.assertEqual(campaign.spent, Decimal("0.05"))
        self.assertEqual(wallet_balance(self.fan), FAN_DISCOVERY_REWARD)

    def test_campaign_completes_and_sets_cooldown_when_spent(self):
        campaign = self.make_active_campaign(budget=Decimal("5.00"), spent=Decimal("4.90"))
        # purchase rate is 1.00 but capped at remaining 0.10
        charge_engagement(Campaign.TRACK, self.track.id, self.fan, "purchase")
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, Campaign.COMPLETED)
        self.assertIsNotNone(campaign.cooldown_until)


class RedemptionTests(PromotionTestBase):
    def test_redeem_for_tip_debits_wallet(self):
        record_ledger_entry(
            self.fan,
            PromotionLedgerEntry.REWARD,
            Decimal("1.00"),
            description="Test reward balance",
        )
        from promotions.redemption import redeem_for_tip

        redeemed, error = redeem_for_tip(self.fan, Decimal("5.00"), artist_label="Boom Artist")
        self.assertEqual(error, "")
        self.assertEqual(redeemed, Decimal("1.00"))
        self.assertEqual(wallet_balance(self.fan), Decimal("0.00"))
        entry = PromotionLedgerEntry.objects.filter(user=self.fan, entry_type=PromotionLedgerEntry.REDEEM).first()
        self.assertIsNotNone(entry)

    def test_redeem_preview_endpoint(self):
        record_ledger_entry(self.fan, PromotionLedgerEntry.REWARD, Decimal("0.75"))
        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/promotions/wallet/redeem-preview/?amount=5&kind=tip")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["applicable"], "0.75")
        self.assertTrue(response.data["can_apply"])

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_tip_applies_discovery_credits(self):
        record_ledger_entry(self.fan, PromotionLedgerEntry.REWARD, Decimal("0.50"))
        self.client.force_authenticate(self.fan)
        response = self.client.post(
            "/api/subscriptions/tips/",
            {
                "artist_id": self.artist.id,
                "profession": "music",
                "amount": "5.00",
                "apply_discovery_credits": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["discovery_credits_applied"], "0.50")
        self.assertEqual(response.data["wallet_balance"], "0.00")


class InvariantTests(PromotionTestBase):
    def test_wallet_exposes_invariants_and_tagline(self):
        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/promotions/wallet/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["tagline"], DISCOVERY_ADS_TAGLINE)
        self.assertTrue(response.data["invariants"]["no_bidding"])
        self.assertEqual(response.data["invariants"]["max_budget"], str(CAMPAIGN_MAX_BUDGET))

    def test_promotion_invariants_match_platform_fees(self):
        invariants = promotion_invariants()
        self.assertEqual(invariants["max_budget"], str(CAMPAIGN_MAX_BUDGET))
        self.assertEqual(invariants["fan_reward_daily_cap"], str(FAN_DISCOVERY_REWARD_DAILY_CAP))
        self.assertTrue(invariants["engagement_billing"])
        self.assertTrue(invariants["escrow_billing"])

    def test_studio_credits_use_grant_ledger_type(self):
        from promotions.services import maybe_grant_studio_monthly_credits

        self.artist.artist_plan = "studio"
        self.artist.save(update_fields=["artist_plan"])
        maybe_grant_studio_monthly_credits(self.artist)
        entry = PromotionLedgerEntry.objects.filter(user=self.artist, entry_type=PromotionLedgerEntry.GRANT).first()
        self.assertIsNotNone(entry)


class DiscoveryScoreTests(PromotionTestBase):
    def test_new_campaign_gets_neutral_score(self):
        campaign = self.make_active_campaign()
        self.assertEqual(compute_discovery_score(campaign), 50.0)

    def test_engagement_improves_score(self):
        campaign = self.make_active_campaign()
        for _ in range(10):
            CampaignEvent.objects.create(campaign=campaign, event_type=CampaignEvent.IMPRESSION)
        for i in range(6):
            f = User.objects.create_user(username=f"f{i}", password="pw", user_type=User.FAN)
            CampaignEvent.objects.create(campaign=campaign, fan=f, event_type=CampaignEvent.FULL_LISTEN)
        score = compute_discovery_score(campaign)
        self.assertGreater(score, 0)


class TargetingTests(PromotionTestBase):
    def test_campaign_matches_fan_by_genre(self):
        self.make_active_campaign(target_genres="hip-hop")
        matched = campaigns_for_fan(Campaign.TRACK, self.fan)
        self.assertEqual(len(matched), 1)

    def test_campaign_matches_fan_by_similar_artist(self):
        peer = User.objects.create_user(username="peer", password="pw", user_type=User.ARTIST)
        ArtistProfile.objects.create(owner=peer, stage_name="Peer Artist", genre="metal", city="Melbourne")
        ArtistFollow.objects.create(fan=self.fan, artist=peer)
        self.make_active_campaign(target_genres="", target_artist_ids=str(peer.id))
        matched = campaigns_for_fan(Campaign.TRACK, self.fan)
        self.assertEqual(len(matched), 1)

    def test_targeting_suggestions_endpoint(self):
        peer = User.objects.create_user(username="peer2", password="pw", user_type=User.ARTIST)
        ArtistProfile.objects.create(owner=peer, stage_name="Peer Two", genre="hip-hop", city="Melbourne")
        fan = User.objects.create_user(username="overlapfan", password="pw", user_type=User.FAN)
        ArtistFollow.objects.create(fan=fan, artist=self.artist)
        ArtistFollow.objects.create(fan=fan, artist=peer)

        self.client.force_authenticate(self.artist)
        response = self.client.get("/api/promotions/targeting/suggestions/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("hip-hop", response.data["target_genres"])
        self.assertGreaterEqual(len(response.data["similar_artists"]), 1)

    def test_create_campaign_accepts_similar_artist_targets(self):
        peer = User.objects.create_user(username="peer3", password="pw", user_type=User.ARTIST)
        ArtistProfile.objects.create(owner=peer, stage_name="Peer Three", genre="hip-hop")
        grant_credits(self.artist, Decimal("50.00"))
        self.client.force_authenticate(self.artist)
        response = self.client.post(
            "/api/promotions/campaigns/",
            {
                "target_type": "track",
                "target_id": self.track.id,
                "budget": "25",
                "target_genres": "hip-hop",
                "target_artist_ids": [peer.id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        campaign = Campaign.objects.get(id=response.data["campaign"]["id"])
        self.assertEqual(campaign.target_artist_id_list(), [peer.id])
        self.assertEqual(len(response.data["campaign"]["target_artists"]), 1)

    def test_campaign_excludes_own_artist(self):
        self.make_active_campaign(target_genres="hip-hop")
        matched = campaigns_for_fan(Campaign.TRACK, self.artist)
        self.assertEqual(len(matched), 0)

    def test_non_matching_genre_filtered_out(self):
        unrelated_fan = User.objects.create_user(
            username="metalfan", password="pw", user_type=User.FAN, favorite_genres="metal",
        )
        self.make_active_campaign(target_genres="hip-hop")
        matched = campaigns_for_fan(Campaign.TRACK, unrelated_fan)
        self.assertEqual(len(matched), 0)


class FanControlsTests(PromotionTestBase):
    def test_fewer_promoted_reduces_injection(self):
        self.make_active_campaign(target_genres="hip-hop")
        self.fan.discovery_fewer_promoted = True
        self.fan.save(update_fields=["discovery_fewer_promoted"])
        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/discovery/tracks/")
        promoted = [r for r in response.data["results"] if r.get("promoted")]
        self.assertLessEqual(len(promoted), 1)

    def test_promoted_genres_only_filters_unmatched(self):
        self.make_active_campaign(target_genres="metal")
        self.fan.favorite_genres = "hip-hop"
        self.fan.discovery_promoted_genres_only = True
        self.fan.save(update_fields=["favorite_genres", "discovery_promoted_genres_only"])
        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/discovery/tracks/")
        promoted = [r for r in response.data["results"] if r.get("promoted")]
        self.assertEqual(len(promoted), 0)


class InjectionTests(PromotionTestBase):
    def test_promoted_track_injected_into_discovery(self):
        self.make_active_campaign(target_genres="hip-hop")
        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/discovery/tracks/")
        self.assertEqual(response.status_code, 200)
        promoted = [r for r in response.data["results"] if r.get("promoted")]
        self.assertTrue(promoted)
        self.assertEqual(promoted[0]["promotion"]["campaign_id"], Campaign.objects.first().id)
        self.assertTrue(
            CampaignEvent.objects.filter(event_type=CampaignEvent.IMPRESSION).exists()
        )


class StudioPlanCreditTests(PromotionTestBase):
    def test_studio_plan_grants_monthly_credits_once(self):
        from promotions.services import maybe_grant_studio_monthly_credits

        self.artist.artist_plan = "studio"
        self.artist.save(update_fields=["artist_plan"])
        first = maybe_grant_studio_monthly_credits(self.artist)
        second = maybe_grant_studio_monthly_credits(self.artist)
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(wallet_balance(self.artist), Decimal("25.00"))

    def test_wallet_endpoint_grants_studio_credits(self):
        self.artist.artist_plan = "studio"
        self.artist.save(update_fields=["artist_plan"])
        self.client.force_authenticate(self.artist)
        response = self.client.get("/api/promotions/wallet/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["balance"], "25.00")
        self.assertEqual(response.data["tagline"], DISCOVERY_ADS_TAGLINE)


class PlacementTests(PromotionTestBase):
    def test_home_placements_return_promoted_track(self):
        campaign = self.make_active_campaign(target_genres="hip-hop")
        self.client.force_authenticate(self.fan)
        response = self.client.get("/api/promotions/placements/?surface=home")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertTrue(response.data["results"][0]["promoted"])
        self.assertEqual(response.data["results"][0]["promotion"]["campaign_id"], campaign.id)
        self.assertEqual(response.data["tagline"], DISCOVERY_ADS_TAGLINE)

    def test_artist_page_excludes_current_artist(self):
        self.make_active_campaign(target_genres="hip-hop")
        self.client.force_authenticate(self.fan)
        response = self.client.get(
            f"/api/promotions/placements/?surface=artist_page&artist_id={self.artist.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])

    def test_placements_require_authentication(self):
        response = self.client.get("/api/promotions/placements/?surface=home")
        self.assertEqual(response.status_code, 401)
