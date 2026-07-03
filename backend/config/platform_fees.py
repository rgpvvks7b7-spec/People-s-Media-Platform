from decimal import Decimal


SUPPORT_PLATFORM_RATE = Decimal("0.10")
TIP_PLATFORM_RATE = Decimal("0.10")
MARKETPLACE_PLATFORM_RATE = Decimal("0.15")
TICKET_PLATFORM_RATE = Decimal("0.15")
COMMISSION_PLATFORM_RATE = Decimal("0.15")

# --- Discovery Ads (promoted releases) ---------------------------------------
# Hard anti-pay-to-win invariants. These are intentionally low and capped so no
# artist can buy their way to dominance; fan response decides reach.
CAMPAIGN_MIN_BUDGET = Decimal("5.00")
CAMPAIGN_MAX_BUDGET = Decimal("100.00")
CAMPAIGN_MAX_ACTIVE = 4
CAMPAIGN_COOLDOWN_DAYS = 3

# Budget is debited per *qualified engagement*, never per impression. This is
# what makes "the audience decides what spreads" technically true and blocks
# impression farming.
CAMPAIGN_ENGAGEMENT_RATES = {
    "full_listen": Decimal("0.15"),
    "save": Decimal("0.25"),
    "follow": Decimal("0.50"),
    "share": Decimal("0.20"),
    "purchase": Decimal("1.00"),
    "feedback_up": Decimal("0.05"),
}

# Credits a fan earns (into the same ledger) for genuine discovery engagement
# with a promoted item plus feedback. Turns ad spend into a two-sided economy.
FAN_DISCOVERY_REWARD = Decimal("0.05")
FAN_DISCOVERY_REWARD_DAILY_CAP = Decimal("1.00")
FAN_CREDIT_MAX_REDEEM_PER_TIP = Decimal("5.00")
FAN_CREDIT_MAX_REDEEM_PER_PURCHASE = Decimal("10.00")

# Marketing copy surfaced in API + UI. Keep server-side so product voice stays consistent.
DISCOVERY_ADS_TAGLINE = (
    "No artist can spend more than $100 on a campaign. The audience decides what spreads next."
)

# Studio plan includes promotion credits granted on plan activation.
STUDIO_PLAN_MONTHLY_CREDITS = Decimal("25.00")

ARTIST_PRO_PLANS = [
    {
        "id": "pro",
        "name": "Artist Pro",
        "monthly_price": Decimal("12.00"),
        "features": [
            "Advanced analytics",
            "Commission inbox",
            "Scheduled drops",
            "Mailing list export",
            "Profile customization",
        ],
    },
    {
        "id": "studio",
        "name": "Studio",
        "monthly_price": Decimal("29.00"),
        "features": [
            "Everything in Artist Pro",
            "Custom domain",
            "Priority support",
            "Promoted drop credits",
            "Deeper fan conversion reports",
        ],
    },
]


def split_amount(amount, platform_rate):
    amount = Decimal(str(amount))
    platform_fee = (amount * platform_rate).quantize(Decimal("0.01"))
    artist_share = amount - platform_fee
    return artist_share, platform_fee


def split_ticket_sale(amount, listing=None):
    """Split a show ticket: platform fee first, then venue door share, remainder to artist."""
    amount = Decimal(str(amount))
    platform_fee = (amount * TICKET_PLATFORM_RATE).quantize(Decimal("0.01"))
    host_share = Decimal("0.00")

    if listing is not None:
        from spaces.models import SpaceListing

        if listing.split_type == SpaceListing.DOOR_PERCENT and listing.host_cut_percent:
            host_share = (
                amount * Decimal(listing.host_cut_percent) / Decimal("100")
            ).quantize(Decimal("0.01"))

    net_after_platform = amount - platform_fee
    if host_share > net_after_platform:
        host_share = net_after_platform
    artist_share = amount - platform_fee - host_share
    return artist_share, platform_fee, host_share


def platform_rate_for_product_type(product_type):
    if product_type == "event_ticket":
        return TICKET_PLATFORM_RATE
    return MARKETPLACE_PLATFORM_RATE


def _whole_percent(rate):
    return f"{(rate * 100).quantize(Decimal('1'))}%"


def fee_schedule():
    """Canonical, display-ready fee disclosure. Single source of truth for the UI."""
    streams = [
        ("support", "Monthly support & subscriptions", SUPPORT_PLATFORM_RATE),
        ("tips", "One-time tips", TIP_PLATFORM_RATE),
        ("marketplace", "Music & merch sales", MARKETPLACE_PLATFORM_RATE),
        ("event_tickets", "Show tickets", TICKET_PLATFORM_RATE),
        ("commission", "Custom commissions", COMMISSION_PLATFORM_RATE),
    ]
    return {
        "items": [
            {
                "id": stream_id,
                "label": label,
                "platform_rate": str(rate),
                "platform_percent": _whole_percent(rate),
                "you_keep_percent": _whole_percent(Decimal("1") - rate),
            }
            for stream_id, label, rate in streams
        ],
        "live_policy": (
            "Show tickets: IndieFund keeps 15%. When your venue uses a door-percent split, "
            "their share is deducted from your ticket earnings automatically — flat-fee deals "
            "are settled outside ticket checkout. IndieFund never takes a cut of food & beverage."
        ),
        "discovery_ads_note": DISCOVERY_ADS_TAGLINE,
    }
