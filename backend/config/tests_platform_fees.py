from decimal import Decimal

from django.test import SimpleTestCase

from config.platform_fees import (
    fee_calculator,
    fee_schedule_for_plan,
    MARKETPLACE_PLATFORM_RATE,
    TICKET_PLATFORM_RATE,
    TIP_PLATFORM_RATE,
    fee_schedule,
    marketplace_rate_for_artist,
    split_ticket_sale,
    support_rate_for_artist,
)


class _FakeArtist:
    def __init__(self, plan):
        self.artist_plan = plan


class PlatformFeesTests(SimpleTestCase):
    def test_ticket_rate_matches_marketplace(self):
        self.assertEqual(TICKET_PLATFORM_RATE, MARKETPLACE_PLATFORM_RATE)

    def test_split_ticket_sale_with_door_percent(self):
        listing = type(
            "Listing",
            (),
            {"split_type": "door_percent", "host_cut_percent": 20},
        )()
        artist_share, platform_fee, host_share = split_ticket_sale("12.00", listing)
        self.assertEqual(platform_fee, Decimal("1.80"))
        self.assertEqual(host_share, Decimal("2.40"))
        self.assertEqual(artist_share, Decimal("7.80"))

    def test_split_ticket_sale_fb_only_has_no_host_share(self):
        listing = type(
            "Listing",
            (),
            {"split_type": "fb_only", "host_cut_percent": 20},
        )()
        artist_share, platform_fee, host_share = split_ticket_sale("12.00", listing)
        self.assertEqual(platform_fee, Decimal("1.80"))
        self.assertEqual(host_share, Decimal("0.00"))
        self.assertEqual(artist_share, Decimal("10.20"))

    def test_fee_schedule_includes_event_tickets(self):
        schedule = fee_schedule()
        items = {item["id"]: item for item in schedule["items"]}
        self.assertEqual(items["event_tickets"]["platform_percent"], "15%")
        self.assertEqual(items["event_tickets"]["you_keep_percent"], "85%")
        self.assertIn("15%", schedule["live_policy"])

    def test_tips_are_fee_free_on_every_plan(self):
        self.assertEqual(TIP_PLATFORM_RATE, Decimal("0.00"))
        schedule = fee_schedule(_FakeArtist("free"))
        items = {item["id"]: item for item in schedule["items"]}
        self.assertEqual(items["tips"]["you_keep_percent"], "100%")

    def test_pro_plan_reduces_support_rate(self):
        self.assertEqual(support_rate_for_artist(_FakeArtist("free")), Decimal("0.10"))
        self.assertEqual(support_rate_for_artist(_FakeArtist("pro")), Decimal("0.05"))
        self.assertEqual(support_rate_for_artist(_FakeArtist("studio")), Decimal("0.05"))

    def test_studio_plan_reduces_marketplace_rate(self):
        self.assertEqual(marketplace_rate_for_artist(_FakeArtist("free")), Decimal("0.15"))
        self.assertEqual(marketplace_rate_for_artist(_FakeArtist("pro")), Decimal("0.15"))
        self.assertEqual(marketplace_rate_for_artist(_FakeArtist("studio")), Decimal("0.12"))

    def test_unknown_plan_falls_back_to_free_rates(self):
        self.assertEqual(support_rate_for_artist(_FakeArtist("")), Decimal("0.10"))
        self.assertEqual(marketplace_rate_for_artist(None), Decimal("0.15"))

    def test_fee_schedule_reflects_plan_discounts(self):
        schedule = fee_schedule(_FakeArtist("studio"))
        items = {item["id"]: item for item in schedule["items"]}
        self.assertEqual(schedule["plan"], "studio")
        self.assertEqual(items["support"]["you_keep_percent"], "95%")
        self.assertEqual(items["marketplace"]["you_keep_percent"], "88%")
        self.assertEqual(items["commission"]["you_keep_percent"], "88%")
        self.assertEqual(items["event_tickets"]["you_keep_percent"], "85%")

    def test_fee_calculator_keeps_tips_whole(self):
        result = fee_calculator("free", support_gmv="100", tips_gmv="50", marketplace_gmv="100")
        self.assertEqual(result["plan"], "free")
        self.assertEqual(result["you_keep_total"], "225.00")
        self.assertEqual(result["platform_total"], "25.00")
        tips = next(line for line in result["lines"] if line["id"] == "tips")
        self.assertEqual(tips["you_keep"], "50.00")

    def test_fee_schedule_for_plan_uses_studio_rates(self):
        schedule = fee_schedule_for_plan("studio")
        items = {item["id"]: item for item in schedule["items"]}
        self.assertEqual(items["support"]["you_keep_percent"], "95%")
        self.assertEqual(items["marketplace"]["you_keep_percent"], "88%")

