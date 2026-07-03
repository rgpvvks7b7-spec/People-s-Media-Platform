from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from config.platform_fees import (
    CAMPAIGN_ENGAGEMENT_RATES,
    CAMPAIGN_COOLDOWN_DAYS,
    CAMPAIGN_MAX_ACTIVE,
    CAMPAIGN_MAX_BUDGET,
    CAMPAIGN_MIN_BUDGET,
    FAN_CREDIT_MAX_REDEEM_PER_PURCHASE,
    FAN_CREDIT_MAX_REDEEM_PER_TIP,
    FAN_DISCOVERY_REWARD,
    FAN_DISCOVERY_REWARD_DAILY_CAP,
    STUDIO_PLAN_MONTHLY_CREDITS,
)

from .models import Campaign, CampaignEvent, PromotionLedgerEntry, normalize_genre_terms

ZERO = Decimal("0.00")


# --- Wallet / ledger ---------------------------------------------------------

def wallet_balance(user):
    if not getattr(user, "is_authenticated", False):
        return ZERO
    total = PromotionLedgerEntry.objects.filter(user=user).aggregate(s=Sum("amount"))["s"]
    return total or ZERO


def record_ledger_entry(user, entry_type, amount, campaign=None, description=""):
    """Append an immutable ledger row and stamp the running balance."""
    amount = Decimal(str(amount))
    with transaction.atomic():
        previous = wallet_balance(user)
        entry = PromotionLedgerEntry.objects.create(
            user=user,
            entry_type=entry_type,
            amount=amount,
            balance_after=previous + amount,
            campaign=campaign,
            description=description[:255],
        )
    return entry


def grant_credits(user, amount, description="Promotion credits"):
    amount = Decimal(str(amount))
    if amount <= ZERO:
        return None
    entry = record_ledger_entry(user, PromotionLedgerEntry.GRANT, amount, description=description)
    fund_pending_draft_campaigns(user)
    return entry


def studio_grant_period(now=None):
    now = now or timezone.now()
    return now.strftime("%Y-%m")


def maybe_grant_studio_monthly_credits(user):
    """Grant included Studio-plan credits once per calendar month."""
    if not getattr(user, "is_authenticated", False):
        return None
    if getattr(user, "artist_plan", "free") != "studio":
        return None
    description = f"Studio plan credits ({studio_grant_period()})"
    if PromotionLedgerEntry.objects.filter(
        user=user,
        entry_type=PromotionLedgerEntry.GRANT,
        description=description,
    ).exists():
        return None
    return grant_credits(user, STUDIO_PLAN_MONTHLY_CREDITS, description=description)


def purchase_credits(user, amount, description="Credit purchase"):
    amount = Decimal(str(amount))
    if amount <= ZERO:
        return None
    entry = record_ledger_entry(user, PromotionLedgerEntry.PURCHASE, amount, description=description)
    fund_pending_draft_campaigns(user)
    return entry


# --- Campaign funding --------------------------------------------------------

def activate_campaign(campaign, provider="wallet"):
    campaign.status = Campaign.ACTIVE
    campaign.activated_at = timezone.now()
    campaign.payment_provider = provider
    campaign.save(update_fields=["status", "activated_at", "payment_provider"])


def try_fund_campaign(campaign, user):
    """Reserve campaign budget in escrow and activate when balance allows."""
    if campaign.status != Campaign.DRAFT:
        return False, "not_draft"
    if campaign.artist_id != user.id:
        return False, "not_owner"

    can_launch, reason = Campaign.can_launch(user)
    if not can_launch:
        return False, reason

    balance = wallet_balance(user)
    if balance < campaign.budget:
        return False, "insufficient_balance"

    record_ledger_entry(
        user,
        PromotionLedgerEntry.SPEND,
        -campaign.budget,
        campaign=campaign,
        description=f"Reserve budget for '{campaign.title}'",
    )
    activate_campaign(campaign, provider="wallet")
    return True, ""


def refund_campaign_escrow(campaign, user, reason=""):
    """Return unused reserved budget to the artist wallet."""
    refund = campaign.remaining_budget
    if refund <= ZERO:
        return None
    return record_ledger_entry(
        user,
        PromotionLedgerEntry.REFUND,
        refund,
        campaign=campaign,
        description=(reason or f"Refund unused budget for '{campaign.title}'")[:255],
    )


def fund_pending_draft_campaigns(user):
    """Launch draft campaigns oldest-first when credits arrive."""
    launched = []
    for campaign in Campaign.objects.filter(artist=user, status=Campaign.DRAFT).order_by("created_at"):
        ok, reason = try_fund_campaign(campaign, user)
        if ok:
            launched.append(campaign)
        elif reason == "insufficient_balance":
            break
        elif reason in {"not_draft", "not_owner"}:
            continue
        else:
            break
    return launched


# --- Targeting / matching ----------------------------------------------------

def fan_taste_terms(user):
    """Build the set of genre terms describing a fan's taste, reusing the same
    signals the discovery engine uses (favorite genres + positive signals)."""
    from discovery.models import ArtistSignal

    terms = set()
    if not getattr(user, "is_authenticated", False):
        return terms
    terms |= normalize_genre_terms(getattr(user, "favorite_genres", "") or "")
    for signal in ArtistSignal.objects.filter(
        fan=user,
        signal_type__in=[ArtistSignal.SAVE, ArtistSignal.MORE_LIKE_THIS],
    ):
        if signal.liked_genre:
            terms |= normalize_genre_terms(signal.liked_genre)
    return terms


def fan_followed_artist_ids(user):
    if not getattr(user, "is_authenticated", False):
        return set()
    from artists.models import ArtistFollow
    from subscriptions.models import FanSubscription

    followed = set(
        ArtistFollow.objects.filter(fan=user).values_list("artist_id", flat=True)
    )
    followed |= set(
        FanSubscription.objects.filter(fan=user, active=True).values_list("artist_id", flat=True)
    )
    return followed


def fan_discovery_prefs(user):
    if not getattr(user, "is_authenticated", False):
        return {
            "prefer_emerging": False,
            "fewer_promoted": False,
            "promoted_genres_only": False,
        }
    return {
        "prefer_emerging": bool(getattr(user, "discovery_prefer_emerging", False)),
        "fewer_promoted": bool(getattr(user, "discovery_fewer_promoted", False)),
        "promoted_genres_only": bool(getattr(user, "discovery_promoted_genres_only", False)),
    }


def campaign_matches_fan(campaign, user, fan_terms=None, fan_location="", followed_ids=None, *, strict_genres=False):
    """Relevance gate. A campaign reaches a fan when ANY targeting facet
    matches, OR when targeting is open (no facets set)."""
    target_terms = campaign.target_genre_terms()
    target_location = (campaign.target_location or "").strip().lower()
    target_artist_ids = set(campaign.target_artist_id_list())

    if strict_genres:
        if not fan_terms:
            fan_terms = fan_taste_terms(user)
        if not fan_terms or not target_terms or not (target_terms & fan_terms):
            return False
        return True

    has_targeting = bool(target_terms or target_location or target_artist_ids)
    if not has_targeting:
        return True

    if fan_terms is None:
        fan_terms = fan_taste_terms(user)
    if followed_ids is None:
        followed_ids = fan_followed_artist_ids(user)
    fan_location = (fan_location or getattr(user, "discovery_location", "") or "").strip().lower()

    if target_terms and (target_terms & fan_terms):
        return True
    if target_location and fan_location and (
        target_location in fan_location or fan_location in target_location
    ):
        return True
    if target_artist_ids and (target_artist_ids & followed_ids):
        return True
    return False


def eligible_campaigns(target_type, target_id=None):
    qs = Campaign.objects.filter(status=Campaign.ACTIVE, target_type=target_type)
    if target_id is not None:
        qs = qs.filter(target_id=target_id)
    return [c for c in qs if c.is_billable]


def campaigns_for_fan(target_type, user, fan_terms=None, fan_location="", followed_ids=None, prefs=None):
    """Active, billable campaigns of a given target type that match this fan,
    excluding the fan's own campaigns. Highest discovery score first."""
    if prefs is None:
        prefs = fan_discovery_prefs(user)
    if fan_terms is None:
        fan_terms = fan_taste_terms(user)
    if followed_ids is None:
        followed_ids = fan_followed_artist_ids(user)
    strict_genres = prefs.get("promoted_genres_only", False)
    matched = []
    for campaign in Campaign.objects.filter(status=Campaign.ACTIVE, target_type=target_type).select_related("artist"):
        if not campaign.is_billable:
            continue
        if getattr(user, "is_authenticated", False) and campaign.artist_id == user.id:
            continue
        if not campaign_matches_fan(
            campaign,
            user,
            fan_terms=fan_terms,
            fan_location=fan_location,
            followed_ids=followed_ids,
            strict_genres=strict_genres,
        ):
            continue
        if prefs.get("prefer_emerging"):
            from artists.business_health import get_artist_business_health

            try:
                profile = campaign.artist.artist_profile
            except Exception:
                continue
            health = get_artist_business_health(campaign.artist, profile)
            if not health.get("is_emerging"):
                continue
        matched.append(campaign)
    matched.sort(key=lambda c: (c.discovery_score, float(c.remaining_budget)), reverse=True)
    return matched


# --- Discovery score ---------------------------------------------------------

def compute_discovery_score(campaign):
    """Blend of fan-response quality. This is the anti-pay-to-win core:
    better-performing campaigns earn more distribution per remaining dollar.
    """
    counts = {
        row["event_type"]: row["n"]
        for row in CampaignEvent.objects.filter(campaign=campaign)
        .values("event_type")
        .annotate(n=Count("id"))
    }
    impressions = counts.get(CampaignEvent.IMPRESSION, 0)
    full_listens = counts.get(CampaignEvent.FULL_LISTEN, 0)
    saves = counts.get(CampaignEvent.SAVE, 0)
    follows = counts.get(CampaignEvent.FOLLOW, 0)
    shares = counts.get(CampaignEvent.SHARE, 0)
    purchases = counts.get(CampaignEvent.PURCHASE, 0)
    up = counts.get(CampaignEvent.FEEDBACK_UP, 0)
    down = counts.get(CampaignEvent.FEEDBACK_DOWN, 0)

    # New campaigns get a neutral starting score so they aren't buried before
    # they have data ("spend buys a fair shot").
    if impressions < 5:
        base = 50.0
    else:
        listen_through = full_listens / impressions
        save_rate = saves / impressions
        follow_rate = follows / impressions
        base = (
            listen_through * 40
            + save_rate * 70
            + follow_rate * 120
            + (shares / impressions) * 60
            + (purchases / impressions) * 200
        )
        base = min(base, 100.0)

    feedback_total = up + down
    if feedback_total:
        sentiment = (up - down) / feedback_total  # -1..1
        base *= (1 + 0.3 * sentiment)

    score = round(max(base, 0.0), 2)
    if campaign.discovery_score != score:
        campaign.discovery_score = score
        campaign.save(update_fields=["discovery_score"])
    return score


# --- Engagement billing ------------------------------------------------------

def _already_charged(campaign, fan, event_type):
    """A given fan can only be billed once per campaign per qualified action."""
    if fan is None or not getattr(fan, "is_authenticated", False):
        return True  # never bill anonymous engagement
    return CampaignEvent.objects.filter(
        campaign=campaign, fan=fan, event_type=event_type
    ).exists()


def record_impression(campaign, fan):
    CampaignEvent.objects.create(
        campaign=campaign,
        fan=fan if getattr(fan, "is_authenticated", False) else None,
        event_type=CampaignEvent.IMPRESSION,
        charge=ZERO,
    )


def _complete_campaign(campaign):
    from config.platform_fees import CAMPAIGN_COOLDOWN_DAYS

    now = timezone.now()
    campaign.status = Campaign.COMPLETED
    campaign.completed_at = now
    campaign.cooldown_until = now + timezone.timedelta(days=CAMPAIGN_COOLDOWN_DAYS)
    campaign.save(update_fields=["status", "completed_at", "cooldown_until"])
    _notify_campaign_completed(campaign)


def charge_engagement(target_type, target_id, fan, event_type, artist=None):
    """Central billing entry point. Finds active campaigns promoting this item,
    bills the engagement against budget (once per fan/action), rewards the fan,
    refreshes the discovery score, and completes the campaign when funds run out.

    Returns the list of campaigns that were charged.
    """
    rate = CAMPAIGN_ENGAGEMENT_RATES.get(event_type)
    charged = []
    campaigns = Campaign.objects.filter(
        status=Campaign.ACTIVE, target_type=target_type, target_id=target_id
    )
    if artist is not None:
        campaigns = campaigns.filter(artist=artist)

    for campaign in campaigns:
        if not campaign.is_billable:
            continue
        if _already_charged(campaign, fan, event_type):
            continue

        charge = ZERO
        if rate is not None:
            charge = min(Decimal(str(rate)), campaign.remaining_budget)

        with transaction.atomic():
            CampaignEvent.objects.create(
                campaign=campaign,
                fan=fan if getattr(fan, "is_authenticated", False) else None,
                event_type=event_type,
                charge=charge,
            )
            if charge > ZERO:
                campaign.spent = (campaign.spent + charge)
                campaign.save(update_fields=["spent"])
                _reward_fan(fan, campaign, event_type, charge)

        compute_discovery_score(campaign)
        if not campaign.is_billable and campaign.status == Campaign.ACTIVE:
            _complete_campaign(campaign)
        charged.append(campaign)

    return charged


def fan_rewards_today(fan, now=None):
    """Total discovery reward credits earned by this fan today."""
    now = now or timezone.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    total = PromotionLedgerEntry.objects.filter(
        user=fan,
        entry_type=PromotionLedgerEntry.REWARD,
        created_at__gte=start,
    ).aggregate(s=Sum("amount"))["s"]
    return total or ZERO


def fan_rewarded_for_campaign(fan, campaign):
    return PromotionLedgerEntry.objects.filter(
        user=fan,
        entry_type=PromotionLedgerEntry.REWARD,
        campaign=campaign,
    ).exists()


def _reward_fan(fan, campaign, event_type, charge):
    """Fans earn a small credit for genuine discovery engagement.

    Guardrails: one reward per campaign per fan, daily cap, billed engagement only.
    Rewards settle through the REWARD ledger entry — never GRANT (which auto-launches drafts).
    """
    if not getattr(fan, "is_authenticated", False):
        return None
    if charge <= ZERO:
        return None
    if event_type not in CampaignEvent.POSITIVE_TYPES:
        return None
    if fan.id == campaign.artist_id:
        return None
    if fan_rewarded_for_campaign(fan, campaign):
        return None
    if fan_rewards_today(fan) + FAN_DISCOVERY_REWARD > FAN_DISCOVERY_REWARD_DAILY_CAP:
        return None

    return record_ledger_entry(
        fan,
        PromotionLedgerEntry.REWARD,
        FAN_DISCOVERY_REWARD,
        campaign=campaign,
        description=f"Discovery reward: {event_type}",
    )


def promotion_invariants():
    """Server-enforced anti-pay-to-win rules exposed to clients."""
    return {
        "min_budget": str(CAMPAIGN_MIN_BUDGET),
        "max_budget": str(CAMPAIGN_MAX_BUDGET),
        "max_active": CAMPAIGN_MAX_ACTIVE,
        "cooldown_days": CAMPAIGN_COOLDOWN_DAYS,
        "engagement_billing": True,
        "escrow_billing": True,
        "no_bidding": True,
        "engagement_rates": {key: str(value) for key, value in CAMPAIGN_ENGAGEMENT_RATES.items()},
        "fan_reward": str(FAN_DISCOVERY_REWARD),
        "fan_reward_daily_cap": str(FAN_DISCOVERY_REWARD_DAILY_CAP),
        "max_redeem_per_tip": str(FAN_CREDIT_MAX_REDEEM_PER_TIP),
        "max_redeem_per_purchase": str(FAN_CREDIT_MAX_REDEEM_PER_PURCHASE),
    }


# --- Notifications -----------------------------------------------------------

def _notify_campaign_completed(campaign):
    try:
        from notifications.services import _create_notification
        from notifications.models import Notification

        _create_notification(
            recipient=campaign.artist,
            notification_type=Notification.PROMOTION,
            title="Your promotion finished",
            body=f"Your campaign used ${campaign.spent} of its ${campaign.budget} budget. See how it performed.",
            target_url="/?page=promote",
        )
    except Exception:
        pass
