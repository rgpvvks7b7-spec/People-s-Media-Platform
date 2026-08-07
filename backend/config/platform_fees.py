from decimal import Decimal


# Tips are fee-free on every plan (2026-08-06 decision: Ko-fi set the market at 0%).
TIP_PLATFORM_RATE = Decimal("0.00")

# Paid artist plans buy down the take rate, so the effective percentage cost
# falls as an artist grows instead of scaling with their success.
PLAN_SUPPORT_RATES = {
    "free": Decimal("0.10"),
    "pro": Decimal("0.05"),
    "studio": Decimal("0.05"),
}
PLAN_MARKETPLACE_RATES = {
    "free": Decimal("0.15"),
    "pro": Decimal("0.15"),
    "studio": Decimal("0.12"),
}

# Free-plan defaults; use the *_rate_for_artist helpers whenever the artist is known.
SUPPORT_PLATFORM_RATE = PLAN_SUPPORT_RATES["free"]
MARKETPLACE_PLATFORM_RATE = PLAN_MARKETPLACE_RATES["free"]
TICKET_PLATFORM_RATE = Decimal("0.15")
COMMISSION_PLATFORM_RATE = PLAN_MARKETPLACE_RATES["free"]


def _artist_plan(artist):
    plan = getattr(artist, "artist_plan", "") or "free"
    return plan if plan in PLAN_SUPPORT_RATES else "free"


def support_rate_for_artist(artist):
    return PLAN_SUPPORT_RATES[_artist_plan(artist)]


def marketplace_rate_for_artist(artist):
    return PLAN_MARKETPLACE_RATES[_artist_plan(artist)]


def commission_rate_for_artist(artist):
    return PLAN_MARKETPLACE_RATES[_artist_plan(artist)]

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
            "5% support take rate (vs 10% on Free)",
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
            "12% marketplace take rate (vs 15%)",
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


def fee_schedule(artist=None):
    """Canonical, display-ready fee disclosure. Single source of truth for the UI.

    When ``artist`` is provided, rates reflect that artist's plan discounts.
    """
    plan = _artist_plan(artist) if artist is not None else "free"
    support_rate = PLAN_SUPPORT_RATES[plan]
    marketplace_rate = PLAN_MARKETPLACE_RATES[plan]
    streams = [
        ("support", "Monthly support & subscriptions", support_rate),
        ("tips", "One-time tips", TIP_PLATFORM_RATE),
        ("marketplace", "Music & merch sales", marketplace_rate),
        ("event_tickets", "Show tickets", TICKET_PLATFORM_RATE),
        ("commission", "Custom commissions", marketplace_rate),
    ]
    return {
        "plan": plan,
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
        "plan_note": (
            "Artist Pro drops the support rate to 5%. Studio also drops music, merch, "
            "and commission sales to 12%. Tips are always fee-free."
        ),
        "live_policy": (
            "Show tickets: IndieFund keeps 15%. When your venue uses a door-percent split, "
            "their share is deducted from your ticket earnings automatically — flat-fee deals "
            "are settled outside ticket checkout. IndieFund never takes a cut of food & beverage."
        ),
        "discovery_ads_note": DISCOVERY_ADS_TAGLINE,
    }


class _PlanArtist:
    def __init__(self, plan):
        self.artist_plan = plan


def fee_schedule_for_plan(plan="free"):
    plan = plan if plan in PLAN_SUPPORT_RATES else "free"
    return fee_schedule(_PlanArtist(plan))


def _money(value):
    try:
        amount = Decimal(str(value if value not in {"", None} else "0"))
    except Exception:
        amount = Decimal("0")
    if amount < 0:
        amount = Decimal("0")
    return amount.quantize(Decimal("0.01"))


def fee_calculator(plan="free", *, support_gmv=0, tips_gmv=0, marketplace_gmv=0):
    """Interactive keep-vs-fee estimate for the public pricing page."""
    plan = plan if plan in PLAN_SUPPORT_RATES else "free"
    support_rate = PLAN_SUPPORT_RATES[plan]
    marketplace_rate = PLAN_MARKETPLACE_RATES[plan]
    support = _money(support_gmv)
    tips = _money(tips_gmv)
    marketplace = _money(marketplace_gmv)

    lines = []
    for stream_id, label, amount, rate in [
        ("support", "Monthly support", support, support_rate),
        ("tips", "Tips", tips, TIP_PLATFORM_RATE),
        ("marketplace", "Store / merch", marketplace, marketplace_rate),
    ]:
        artist_share, platform_fee = split_amount(amount, rate)
        lines.append({
            "id": stream_id,
            "label": label,
            "gmv": str(amount),
            "platform_rate": str(rate),
            "platform_percent": _whole_percent(rate),
            "you_keep": str(artist_share),
            "platform_fee": str(platform_fee),
        })

    gmv_total = support + tips + marketplace
    platform_total = sum((Decimal(line["platform_fee"]) for line in lines), Decimal("0.00"))
    you_keep_total = gmv_total - platform_total
    effective = (
        (platform_total / gmv_total).quantize(Decimal("0.0001"))
        if gmv_total > 0
        else Decimal("0")
    )
    return {
        "plan": plan,
        "lines": lines,
        "gmv_total": str(gmv_total),
        "you_keep_total": str(you_keep_total.quantize(Decimal("0.01"))),
        "platform_total": str(platform_total.quantize(Decimal("0.01"))),
        "effective_rate": str(effective),
        "effective_rate_percent": _whole_percent(effective) if gmv_total > 0 else "0%",
    }
