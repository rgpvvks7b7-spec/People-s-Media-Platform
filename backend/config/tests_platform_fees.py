from decimal import Decimal

from django.test import SimpleTestCase

from config.platform_fees import (
    MARKETPLACE_PLATFORM_RATE,
    TICKET_PLATFORM_RATE,
    fee_schedule,
    split_ticket_sale,
)


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
