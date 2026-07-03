from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response

from config.platform_fees import (
    CAMPAIGN_ENGAGEMENT_RATES,
    CAMPAIGN_MAX_ACTIVE,
    CAMPAIGN_MAX_BUDGET,
    CAMPAIGN_MIN_BUDGET,
    DISCOVERY_ADS_TAGLINE,
    FAN_DISCOVERY_REWARD,
    FAN_DISCOVERY_REWARD_DAILY_CAP,
    FAN_CREDIT_MAX_REDEEM_PER_PURCHASE,
    FAN_CREDIT_MAX_REDEEM_PER_TIP,
)
from config.throttling import CheckoutRateThrottle, PromotionRateThrottle
from config.stripe_checkout import demo_mode_allowed

from .models import Campaign, CampaignEvent, Genre, PromotionLedgerEntry, normalize_genre_terms
from .placements import placements_for_surface
from .redemption import redeemable_for_transaction
from .targeting import (
    MAX_SIMILAR_ARTIST_TARGETS,
    build_targeting_suggestions,
    resolve_target_artists,
    search_target_artists,
)
from .services import (
    activate_campaign,
    charge_engagement,
    compute_discovery_score,
    fan_rewards_today,
    fund_pending_draft_campaigns,
    maybe_grant_studio_monthly_credits,
    promotion_invariants,
    purchase_credits,
    refund_campaign_escrow,
    try_fund_campaign,
    wallet_balance,
)

User = get_user_model()

try:
    import stripe
except ImportError:
    stripe = None


# --- target resolution -------------------------------------------------------

def resolve_target(artist, target_type, target_id):
    """Return (label, error). Verifies the artist owns the promoted item."""
    try:
        target_id = int(target_id)
    except (TypeError, ValueError):
        return None, "Invalid target id."

    if target_type == Campaign.TRACK:
        from mediahub.models import MusicUpload

        obj = MusicUpload.objects.filter(id=target_id, artist=artist).first()
        return (obj.title if obj else None), (None if obj else "Track not found or not yours.")
    if target_type == Campaign.POST:
        from posts.models import Post

        obj = Post.objects.filter(id=target_id, author=artist).first()
        return (obj.title or "Post" if obj else None), (None if obj else "Post not found or not yours.")
    if target_type == Campaign.PRODUCT:
        from marketplace.models import Product

        obj = Product.objects.filter(id=target_id, artist=artist).first()
        return (obj.title if obj else None), (None if obj else "Product not found or not yours.")
    if target_type == Campaign.PROFILE:
        if target_id != artist.id:
            return None, "You can only promote your own profile."
        return artist.username, None
    if target_type == Campaign.LIVESTREAM:
        return "Live stream", None
    return None, "Invalid target type."


def serialize_campaign(campaign, include_analytics=False, user=None):
    data = {
        "id": campaign.id,
        "target_type": campaign.target_type,
        "target_id": campaign.target_id,
        "title": campaign.title,
        "budget": str(campaign.budget),
        "spent": str(campaign.spent),
        "remaining_budget": str(campaign.remaining_budget),
        "status": campaign.status,
        "target_genres": campaign.target_genres,
        "target_location": campaign.target_location,
        "target_artist_ids": campaign.target_artist_id_list(),
        "target_artists": resolve_target_artists(campaign),
        "discovery_score": campaign.discovery_score,
        "created_at": campaign.created_at,
        "activated_at": campaign.activated_at,
        "completed_at": campaign.completed_at,
    }
    if user and campaign.status == Campaign.DRAFT:
        balance = wallet_balance(user)
        data["can_launch"] = balance >= campaign.budget
        data["shortfall"] = str(max(campaign.budget - balance, Decimal("0.00")))
    if include_analytics:
        data["analytics"] = campaign_analytics(campaign)
    return data


def campaign_analytics(campaign):
    from django.db.models import Count

    counts = {
        row["event_type"]: row["n"]
        for row in CampaignEvent.objects.filter(campaign=campaign)
        .values("event_type")
        .annotate(n=Count("id"))
    }
    impressions = counts.get(CampaignEvent.IMPRESSION, 0)
    full_listens = counts.get(CampaignEvent.FULL_LISTEN, 0)
    follows = counts.get(CampaignEvent.FOLLOW, 0)
    saves = counts.get(CampaignEvent.SAVE, 0)
    purchases = counts.get(CampaignEvent.PURCHASE, 0)
    spent = campaign.spent

    def per(metric):
        return str((spent / metric).quantize(Decimal("0.01"))) if metric else None

    return {
        "impressions": impressions,
        "full_listens": full_listens,
        "saves": saves,
        "follows": follows,
        "shares": counts.get(CampaignEvent.SHARE, 0),
        "purchases": purchases,
        "feedback_up": counts.get(CampaignEvent.FEEDBACK_UP, 0),
        "feedback_down": counts.get(CampaignEvent.FEEDBACK_DOWN, 0),
        "listen_through_rate": round(full_listens / impressions, 3) if impressions else 0,
        "cost_per_follower": per(follows),
        "cost_per_supporter": per(purchases),
    }


# --- endpoints ---------------------------------------------------------------

@api_view(["GET"])
def index(request):
    return Response({"app": "promotions", "status": "ready"})


@api_view(["GET"])
def wallet(request):
    if not request.user.is_authenticated:
        return Response({
            "balance": "0.00",
            "entries": [],
            "authenticated": False,
            "tagline": DISCOVERY_ADS_TAGLINE,
            "invariants": promotion_invariants(),
        })

    if request.user.user_type == User.ARTIST:
        maybe_grant_studio_monthly_credits(request.user)

    balance = wallet_balance(request.user).quantize(Decimal("0.01"))
    rewards_today = fan_rewards_today(request.user).quantize(Decimal("0.01"))
    entries = PromotionLedgerEntry.objects.filter(user=request.user)[:50]
    payload = {
        "authenticated": True,
        "balance": str(balance),
        "max_budget": str(CAMPAIGN_MAX_BUDGET),
        "min_budget": str(CAMPAIGN_MIN_BUDGET),
        "max_active": CAMPAIGN_MAX_ACTIVE,
        "tagline": DISCOVERY_ADS_TAGLINE,
        "invariants": promotion_invariants(),
        "fan_reward": str(FAN_DISCOVERY_REWARD),
        "fan_reward_daily_cap": str(FAN_DISCOVERY_REWARD_DAILY_CAP),
        "rewards_today": str(rewards_today),
        "rewards_remaining_today": str(
            max(FAN_DISCOVERY_REWARD_DAILY_CAP - rewards_today, Decimal("0.00")).quantize(Decimal("0.01"))
        ),
        "can_redeem": balance > Decimal("0.00"),
        "max_redeem_per_tip": str(FAN_CREDIT_MAX_REDEEM_PER_TIP),
        "max_redeem_per_purchase": str(FAN_CREDIT_MAX_REDEEM_PER_PURCHASE),
        "is_artist": request.user.user_type == User.ARTIST,
        "entries": [
            {
                "id": e.id,
                "entry_type": e.entry_type,
                "amount": str(e.amount),
                "balance_after": str(e.balance_after),
                "description": e.description,
                "campaign_id": e.campaign_id,
                "created_at": e.created_at,
            }
            for e in entries
        ],
    }
    return Response(payload)


@api_view(["GET"])
def genres(request):
    return Response({
        "results": [
            {"slug": g.slug, "name": g.name}
            for g in Genre.objects.all()
        ],
    })


@api_view(["GET"])
def targeting_suggestions(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    track_id = request.query_params.get("track_id")
    return Response(build_targeting_suggestions(request.user, request, track_id=track_id))


@api_view(["GET"])
def targeting_search(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    query = request.query_params.get("q") or ""
    limit = request.query_params.get("limit") or 8
    results = search_target_artists(request.user, request, query=query, limit=limit)
    return Response({"results": results, "count": len(results)})


@api_view(["GET"])
def redeem_preview(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        amount = Decimal(str(request.query_params.get("amount") or "0"))
    except (InvalidOperation, ValueError):
        return Response({"error": "Amount must be a number."}, status=status.HTTP_400_BAD_REQUEST)

    kind = (request.query_params.get("kind") or "tip").strip()
    max_redeem = FAN_CREDIT_MAX_REDEEM_PER_TIP if kind == "tip" else FAN_CREDIT_MAX_REDEEM_PER_PURCHASE
    applicable = redeemable_for_transaction(request.user, amount, max_redeem=max_redeem)
    balance = wallet_balance(request.user).quantize(Decimal("0.01"))

    return Response({
        "balance": str(balance),
        "transaction_amount": str(amount.quantize(Decimal("0.01"))),
        "applicable": str(applicable),
        "max_redeem": str(max_redeem),
        "can_apply": applicable > Decimal("0.00"),
    })


@api_view(["GET", "POST"])
def campaigns(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == "GET":
        mine = Campaign.objects.filter(artist=request.user)
        return Response({
            "results": [serialize_campaign(c, include_analytics=True, user=request.user) for c in mine],
            "balance": str(wallet_balance(request.user).quantize(Decimal("0.01"))),
        })

    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    target_type = (request.data.get("target_type") or Campaign.TRACK).strip()
    if target_type not in dict(Campaign.TARGET_TYPES):
        return Response({"error": "Invalid target type"}, status=status.HTTP_400_BAD_REQUEST)

    label, target_error = resolve_target(request.user, target_type, request.data.get("target_id"))
    if target_error:
        return Response({"error": target_error}, status=status.HTTP_400_BAD_REQUEST)

    try:
        budget = Decimal(str(request.data.get("budget") or CAMPAIGN_MIN_BUDGET))
    except (InvalidOperation, ValueError):
        return Response({"error": "Budget must be a number."}, status=status.HTTP_400_BAD_REQUEST)
    if budget > CAMPAIGN_MAX_BUDGET:
        return Response(
            {"error": f"Campaign budget is capped at ${CAMPAIGN_MAX_BUDGET}. The audience decides what spreads next."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if budget < CAMPAIGN_MIN_BUDGET:
        return Response({"error": f"Minimum campaign budget is ${CAMPAIGN_MIN_BUDGET}."}, status=status.HTTP_400_BAD_REQUEST)

    can_launch, reason = Campaign.can_launch(request.user)
    if not can_launch:
        return Response({"error": reason}, status=status.HTTP_400_BAD_REQUEST)

    target_genres = " ".join(sorted(normalize_genre_terms(request.data.get("target_genres") or "")))
    target_location = (request.data.get("target_location") or "").strip()[:120]
    raw_ids = request.data.get("target_artist_ids") or ""
    if isinstance(raw_ids, list):
        raw_ids = ",".join(str(x) for x in raw_ids)
    target_artist_ids = ",".join(
        part.strip() for part in str(raw_ids).split(",") if part.strip().isdigit()
    )
    id_list = [int(x) for x in target_artist_ids.split(",") if x]
    if len(id_list) > MAX_SIMILAR_ARTIST_TARGETS:
        return Response(
            {"error": f"You can target up to {MAX_SIMILAR_ARTIST_TARGETS} similar artists."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    invalid_ids = [
        artist_id for artist_id in id_list
        if artist_id == request.user.id
        or not User.objects.filter(id=artist_id, user_type=User.ARTIST).exists()
    ]
    if invalid_ids:
        return Response({"error": "One or more similar artists are invalid."}, status=status.HTTP_400_BAD_REQUEST)

    campaign = Campaign.objects.create(
        artist=request.user,
        target_type=target_type,
        target_id=int(request.data.get("target_id")) if target_type != Campaign.LIVESTREAM else int(request.data.get("target_id") or 0),
        title=(request.data.get("title") or label or "")[:180],
        budget=budget,
        target_genres=target_genres,
        target_location=target_location,
        target_artist_ids=target_artist_ids,
        status=Campaign.DRAFT,
    )

    balance = wallet_balance(request.user)
    if balance >= budget:
        ok, reason = try_fund_campaign(campaign, request.user)
        if not ok:
            return Response({"error": reason}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "campaign": serialize_campaign(campaign, user=request.user),
            "funded_from": "wallet",
            "balance": str(wallet_balance(request.user).quantize(Decimal("0.01"))),
        }, status=status.HTTP_201_CREATED)

    return Response({
        "campaign": serialize_campaign(campaign, user=request.user),
        "needs_credits": True,
        "shortfall": str(budget - balance),
        "balance": str(balance.quantize(Decimal("0.01"))),
        "message": "Add promotion credits to launch this campaign.",
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def campaign_action(request, campaign_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        campaign = Campaign.objects.get(id=campaign_id, artist=request.user)
    except Campaign.DoesNotExist:
        return Response({"error": "Campaign not found"}, status=status.HTTP_404_NOT_FOUND)

    action = (request.data.get("action") or "").strip()
    if action == "launch" and campaign.status == Campaign.DRAFT:
        ok, reason = try_fund_campaign(campaign, request.user)
        if not ok:
            messages = {
                "insufficient_balance": "Add more promotion credits to launch this campaign.",
                "not_draft": "Campaign is not a draft.",
            }
            return Response({"error": messages.get(reason, reason)}, status=status.HTTP_400_BAD_REQUEST)
    elif action == "pause" and campaign.status == Campaign.ACTIVE:
        campaign.status = Campaign.PAUSED
        campaign.save(update_fields=["status"])
    elif action == "resume" and campaign.status == Campaign.PAUSED:
        if campaign.remaining_budget <= Decimal("0.00"):
            return Response({"error": "No remaining budget."}, status=status.HTTP_400_BAD_REQUEST)
        campaign.status = Campaign.ACTIVE
        campaign.save(update_fields=["status"])
    elif action == "cancel" and campaign.status in {Campaign.ACTIVE, Campaign.PAUSED, Campaign.DRAFT}:
        if campaign.status != Campaign.DRAFT:
            refund_campaign_escrow(campaign, request.user)
        campaign.status = Campaign.CANCELLED
        campaign.completed_at = timezone.now()
        campaign.save(update_fields=["status", "completed_at"])
    else:
        return Response({"error": "Invalid action for current status."}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"campaign": serialize_campaign(campaign, include_analytics=True, user=request.user)})


@api_view(["POST"])
@throttle_classes([CheckoutRateThrottle])
def buy_credits(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        amount = Decimal(str(request.data.get("amount") or "0"))
    except (InvalidOperation, ValueError):
        return Response({"error": "Amount must be a number."}, status=status.HTTP_400_BAD_REQUEST)
    if amount < CAMPAIGN_MIN_BUDGET:
        return Response({"error": f"Minimum top-up is ${CAMPAIGN_MIN_BUDGET}."}, status=status.HTTP_400_BAD_REQUEST)

    # Demo / local fallback grants credits instantly (mirrors subscriptions).
    if demo_mode_allowed():
        purchase_credits(request.user, amount, description="Demo credit purchase")
        launched = Campaign.objects.filter(
            artist=request.user,
            status=Campaign.ACTIVE,
        ).order_by("-activated_at")[:3]
        return Response({
            "demo": True,
            "balance": str(wallet_balance(request.user).quantize(Decimal("0.01"))),
            "message": f"Added ${amount} in promotion credits (demo).",
            "launched_campaigns": [serialize_campaign(c, user=request.user) for c in launched],
        })

    if stripe is None or not settings.STRIPE_SECRET_KEY:
        return Response({"error": "Stripe is not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            success_url=f"{settings.FRONTEND_URL}/?promote=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/?promote=cancelled",
            customer_email=request.user.email or None,
            line_items=[{
                "price_data": {
                    "currency": settings.STRIPE_CURRENCY,
                    "product_data": {"name": "Promotion credits"},
                    "unit_amount": int(amount * Decimal("100")),
                },
                "quantity": 1,
            }],
            metadata={
                "purchase_type": "promotion_credits",
                "user_id": str(request.user.id),
                "amount": str(amount),
            },
        )
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "checkout_url": checkout_session.url,
        "checkout_session_id": checkout_session.id,
    })


@api_view(["POST"])
@throttle_classes([PromotionRateThrottle])
def feedback(request):
    """Fan feedback on a promoted item: 'up' (would listen again) or 'down'."""
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    campaign_id = request.data.get("campaign_id")
    verdict = (request.data.get("verdict") or "").strip()
    if verdict not in {"up", "down"}:
        return Response({"error": "verdict must be 'up' or 'down'."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return Response({"error": "Campaign not found"}, status=status.HTTP_404_NOT_FOUND)

    if verdict == "up":
        if CampaignEvent.objects.filter(
            campaign=campaign, fan=request.user, event_type=CampaignEvent.FEEDBACK_UP
        ).exists():
            return Response({"message": "Feedback already recorded."})
        charge_engagement(
            campaign.target_type,
            campaign.target_id,
            request.user,
            CampaignEvent.FEEDBACK_UP,
            artist=campaign.artist,
        )
    else:
        CampaignEvent.objects.get_or_create(
            campaign=campaign,
            fan=request.user,
            event_type=CampaignEvent.FEEDBACK_DOWN,
        )
    score = compute_discovery_score(campaign)
    balance = wallet_balance(request.user).quantize(Decimal("0.01"))
    return Response({
        "message": "Feedback recorded.",
        "discovery_score": score,
        "wallet_balance": str(balance),
        "rewards_today": str(fan_rewards_today(request.user).quantize(Decimal("0.01"))),
    })


@api_view(["GET"])
def promotion_placements(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    surface = (request.query_params.get("surface") or "home").strip()
    if surface not in {"home", "artist_page"}:
        return Response({"error": "surface must be 'home' or 'artist_page'."}, status=status.HTTP_400_BAD_REQUEST)

    artist_id = request.query_params.get("artist_id")
    if artist_id is not None:
        try:
            artist_id = int(artist_id)
        except (TypeError, ValueError):
            return Response({"error": "Invalid artist_id."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        limit = int(request.query_params.get("limit") or 2)
    except (TypeError, ValueError):
        return Response({"error": "Invalid limit."}, status=status.HTTP_400_BAD_REQUEST)

    results = placements_for_surface(
        request,
        surface,
        artist_id=artist_id,
        limit=limit,
    )
    return Response({
        "surface": surface,
        "results": results,
        "tagline": DISCOVERY_ADS_TAGLINE,
    })


@api_view(["POST"])
@throttle_classes([PromotionRateThrottle])
def share_promoted(request):
    """Record a fan sharing a promoted item — bills engagement and may reward the fan."""
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    campaign_id = request.data.get("campaign_id")
    try:
        campaign = Campaign.objects.get(id=campaign_id, status=Campaign.ACTIVE)
    except Campaign.DoesNotExist:
        return Response({"error": "Active campaign not found"}, status=status.HTTP_404_NOT_FOUND)

    if campaign.artist_id == request.user.id:
        return Response({"error": "You cannot share your own promotion."}, status=status.HTTP_400_BAD_REQUEST)

    charged = charge_engagement(
        campaign.target_type,
        campaign.target_id,
        request.user,
        CampaignEvent.SHARE,
        artist=campaign.artist,
    )
    balance = wallet_balance(request.user).quantize(Decimal("0.01"))
    return Response({
        "message": "Share recorded.",
        "charged_campaigns": len(charged),
        "wallet_balance": str(balance),
        "rewards_today": str(fan_rewards_today(request.user).quantize(Decimal("0.01"))),
    })
