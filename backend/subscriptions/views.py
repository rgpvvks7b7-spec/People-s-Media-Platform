from decimal import Decimal, InvalidOperation
import logging
from django.conf import settings
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from artists.contact_utils import request_bool, revoke_artist_fan_contact, sync_artist_fan_contact
from artists.journey import log_fan_journey_event
from artists.models import ArtistFanContact, FanJourneyEvent
from artists.models import ArtistProfile
from config.platform_fees import split_amount, support_rate_for_artist
from config.platform_mode import fan_experience_guard
from config.throttling import CheckoutRateThrottle
from config.billing_guard import billing_allowed
from config.stripe_checkout import (
    build_checkout_session,
    cancel_stripe_subscription,
    connect_account_for_artist,
    create_tip_checkout_session,
    demo_mode_allowed,
    refund_charge,
    stripe_ready,
    subscription_connect_params,
)
from notifications.purchase_notifications import notify_payment_failed, notify_subscription_started
from .models import FanSubscription, OneTimeTip, SupportTier

try:
    import stripe
except ImportError:
    stripe = None

User = get_user_model()
logger = logging.getLogger("indiefund.stripe")


def parse_monthly_amount(value):
    try:
        monthly_amount = Decimal(str(value or "1.00"))
    except (InvalidOperation, ValueError):
        return None, "Monthly amount must be a valid number."

    if monthly_amount < Decimal("1.00"):
        monthly_amount = Decimal("1.00")

    return monthly_amount, ""


def parse_tip_amount(value):
    try:
        amount = Decimal(str(value or "1.00"))
    except (InvalidOperation, ValueError):
        return None, "Tip amount must be a valid number."

    if amount < Decimal("1.00"):
        amount = Decimal("1.00")

    return amount, ""


def parse_billing_date(value):
    try:
        billing_date = int(value or 1)
    except (TypeError, ValueError):
        return None, "Billing date must be a number from 1 to 31."

    if billing_date < 1 or billing_date > 31:
        return None, "Billing date must be from 1 to 31."

    return billing_date, ""


def get_artist_or_error(artist_id):
    try:
        artist = User.objects.get(id=artist_id)
    except User.DoesNotExist:
        return None, Response({"error": "Artist not found"}, status=status.HTTP_404_NOT_FOUND)

    if artist.user_type != User.ARTIST or not hasattr(artist, "artist_profile"):
        return None, Response({"error": "Artist profile not found"}, status=status.HTTP_400_BAD_REQUEST)

    return artist, None


def get_profession_or_error(artist, value):
    profession = (value or ArtistProfile.DEFAULT_PROFESSION).strip()
    if profession not in ArtistProfile.valid_profession_keys():
        return None, Response({"error": "Invalid profession"}, status=status.HTTP_400_BAD_REQUEST)

    if not artist.artist_profile.has_profession(profession):
        return None, Response({"error": "Artist does not offer this profession"}, status=status.HTTP_400_BAD_REQUEST)

    return profession, None


def get_tier_and_amount(request, artist, profession):
    tier = None
    if request.data.get("tier_id"):
        try:
            tier = SupportTier.objects.get(
                id=request.data.get("tier_id"),
                artist=artist,
                profession=profession,
                is_active=True,
            )
        except SupportTier.DoesNotExist:
            return None, None, "Support tier not found"
        return tier, tier.monthly_amount, ""

    monthly_amount, amount_error = parse_monthly_amount(request.data.get("monthly_amount", "1.00"))
    return tier, monthly_amount, amount_error


def serialize_tier(tier):
    artist_share, platform_fee = split_amount(tier.monthly_amount, support_rate_for_artist(tier.artist))
    return {
        "id": tier.id,
        "artist_id": tier.artist.id,
        "artist": tier.artist.username,
        "profession": tier.profession,
        "profession_label": ArtistProfile.profession_label(tier.profession),
        "name": tier.name,
        "description": tier.description,
        "monthly_amount": str(tier.monthly_amount),
        "artist_share": str(artist_share),
        "platform_fee": str(platform_fee),
        "benefits": tier.benefits,
        "is_active": tier.is_active,
        "created_at": tier.created_at,
    }


def create_local_demo_subscription(fan, artist, profession, monthly_amount, tier=None, share_email=False, referral_source=""):
    sub, created = FanSubscription.objects.update_or_create(
        fan=fan,
        artist=artist,
        profession=profession,
        defaults={
            "tier": tier,
            "monthly_amount": monthly_amount,
            "billing_date": 1,
            "active": True,
            "payment_provider": "demo",
            "stripe_status": "active",
        },
    )
    contact = sync_artist_fan_contact(
        fan,
        artist,
        source=ArtistFanContact.SUPPORT_PROMPT if share_email else ArtistFanContact.SIGNUP_OPT_IN,
        explicit_share=share_email,
    )
    log_fan_journey_event(
        FanJourneyEvent.SUBSCRIBE,
        artist,
        fan=fan,
        metadata={
            "profession": profession,
            "monthly_amount": str(sub.monthly_amount),
            "source": "checkout",
            "referral_source": referral_source,
        },
    )
    notify_subscription_started(
        fan,
        artist,
        profession=profession,
        monthly_amount=str(sub.monthly_amount),
        payment_provider="demo",
    )

    return Response({
        "created": created,
        "demo": True,
        "message": f"Demo support active: {fan.username} supports {artist.username}'s {ArtistProfile.profession_label(profession)} for ${sub.monthly_amount}/month.",
        "monthly_amount": str(sub.monthly_amount),
        "artist_share": str(sub.artist_share),
        "platform_fee": str(sub.platform_fee),
        "profession": sub.profession,
        "profession_label": ArtistProfile.profession_label(sub.profession),
        "tier_id": sub.tier_id,
        "tier_name": sub.tier.name if sub.tier else "Supporter",
        "email_shared": bool(contact and contact.email_shared),
    })


def serialize_tip(tip):
    return {
        "id": tip.id,
        "fan_id": tip.fan.id,
        "fan": tip.fan.username,
        "artist_id": tip.artist.id,
        "artist": tip.artist.username,
        "profession": tip.profession,
        "profession_label": ArtistProfile.profession_label(tip.profession),
        "amount": str(tip.amount),
        "artist_share": str(tip.artist_share),
        "platform_fee": str(tip.platform_fee),
        "message": tip.message,
        "is_public": tip.is_public,
        "payment_provider": tip.payment_provider,
        "created_at": tip.created_at,
    }

@api_view(["GET"])
def subscription_list(request):
    if not request.user.is_authenticated:
        return Response({
            "subscriptions": [],
            "fan_totals": {},
            "artist_totals": {},
        })

    subs = FanSubscription.objects.select_related("fan", "artist").filter(active=True)
    if request.user.user_type == User.ARTIST:
        subs = subs.filter(Q(artist=request.user) | Q(fan=request.user))
    else:
        subs = subs.filter(fan=request.user)

    subs = subs.order_by("-started_at")

    data = []
    fan_totals = {}
    artist_totals = {}

    for sub in subs:
        fan_totals[sub.fan.username] = fan_totals.get(sub.fan.username, Decimal("0.00")) + sub.monthly_amount
        artist_totals[sub.artist.username] = artist_totals.get(sub.artist.username, Decimal("0.00")) + sub.artist_share

        data.append({
            "id": sub.id,
            "fan_id": sub.fan.id,
            "fan": sub.fan.username,
            "artist_id": sub.artist.id,
            "artist": sub.artist.username,
            "profession": sub.profession,
            "profession_label": ArtistProfile.profession_label(sub.profession),
            "tier_id": sub.tier_id,
            "tier_name": sub.tier.name if sub.tier else "Supporter",
            "monthly_amount": str(sub.monthly_amount),
            "artist_share": str(sub.artist_share),
            "platform_fee": str(sub.platform_fee),
            "billing_date": sub.billing_date,
            "active": sub.active,
            "payment_provider": sub.payment_provider,
            "stripe_status": sub.stripe_status,
            "started_at": sub.started_at,
        })

    return Response({
        "subscriptions": data,
        "fan_totals": {k: str(v) for k, v in fan_totals.items()},
        "artist_totals": {k: str(v) for k, v in artist_totals.items()},
    })


@api_view(["GET", "POST"])
def support_tiers(request):
    if request.method == "GET":
        artist_id = request.query_params.get("artist_id")
        profession = request.query_params.get("profession")
        tiers = SupportTier.objects.select_related("artist").filter(is_active=True)
        if artist_id:
            tiers = tiers.filter(artist_id=artist_id)
        if profession:
            tiers = tiers.filter(profession=profession)

        return Response({
            "results": [serialize_tier(tier) for tier in tiers],
            "count": tiers.count(),
        })

    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    profession, profession_error = get_profession_or_error(request.user, request.data.get("profession"))
    if profession_error:
        return profession_error

    name = (request.data.get("name") or "").strip()
    if not name:
        return Response({"error": "Tier name is required"}, status=status.HTTP_400_BAD_REQUEST)

    monthly_amount, amount_error = parse_monthly_amount(request.data.get("monthly_amount", "1.00"))
    if amount_error:
        return Response({"error": amount_error}, status=status.HTTP_400_BAD_REQUEST)

    tier = SupportTier.objects.create(
        artist=request.user,
        profession=profession,
        name=name[:80],
        description=(request.data.get("description") or "").strip(),
        monthly_amount=monthly_amount,
        benefits=(request.data.get("benefits") or "").strip(),
    )

    return Response({
        "message": "Support tier created.",
        "tier": serialize_tier(tier),
    }, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def tips(request):
    if request.method == "GET":
        artist_id = request.query_params.get("artist_id")
        profession = request.query_params.get("profession")

        if artist_id:
            queryset = OneTimeTip.objects.select_related("fan", "artist").filter(is_public=True, artist_id=artist_id)
            if profession:
                queryset = queryset.filter(profession=profession)
        elif request.user.is_authenticated and request.user.user_type == User.ARTIST:
            queryset = OneTimeTip.objects.select_related("fan", "artist").filter(artist=request.user)
            if profession:
                queryset = queryset.filter(profession=profession)
        elif request.user.is_authenticated:
            queryset = OneTimeTip.objects.select_related("fan", "artist").filter(fan=request.user)
            if profession:
                queryset = queryset.filter(profession=profession)
        else:
            return Response({"error": "artist_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        total_count = queryset.count()
        queryset = queryset.order_by("-created_at")[:50]
        return Response({
            "results": [serialize_tip(tip) for tip in queryset],
            "count": total_count,
        })

    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    blocked = fan_experience_guard(request)
    if blocked:
        return blocked

    allowed, billing_error = billing_allowed(request.user)
    if not allowed:
        return Response({"error": billing_error}, status=status.HTTP_403_FORBIDDEN)

    amount, amount_error = parse_tip_amount(request.data.get("amount", "1.00"))
    if amount_error:
        return Response({"error": amount_error}, status=status.HTTP_400_BAD_REQUEST)

    artist, artist_error = get_artist_or_error(request.data.get("artist_id"))
    if artist_error:
        return artist_error
    profession, profession_error = get_profession_or_error(artist, request.data.get("profession"))
    if profession_error:
        return profession_error

    if request.user == artist:
        return Response({"error": "You cannot tip yourself"}, status=status.HTTP_400_BAD_REQUEST)

    apply_credits = request_bool(request.data, "apply_discovery_credits", False)
    redeemed = Decimal("0.00")
    if apply_credits:
        from promotions.redemption import redeem_for_tip

        artist_label = getattr(getattr(artist, "artist_profile", None), "stage_name", artist.username)
        redeemed, redeem_error = redeem_for_tip(
            request.user,
            amount,
            artist_label=artist_label,
            apply_credits=True,
        )
        if redeem_error:
            return Response({"error": redeem_error}, status=status.HTTP_400_BAD_REQUEST)

    share_email = request_bool(request.data, "share_email_with_artist", False)
    referral_source = (request.data.get("referral_source") or "").strip()[:80]
    message = (request.data.get("message") or "").strip()[:240]

    if demo_mode_allowed():
        tip = OneTimeTip.objects.create(
            fan=request.user,
            artist=artist,
            profession=profession,
            amount=amount,
            message=message,
            is_public=request.data.get("is_public", True) in {True, "true", "1", "on"},
            payment_provider="demo",
        )
        contact = sync_artist_fan_contact(
            request.user,
            artist,
            source=ArtistFanContact.SUPPORT_PROMPT if share_email else ArtistFanContact.SIGNUP_OPT_IN,
            explicit_share=share_email,
        )
        log_fan_journey_event(
            FanJourneyEvent.TIP,
            artist,
            fan=request.user,
            metadata={"profession": profession, "amount": str(tip.amount)},
        )

        from promotions.services import wallet_balance

        return Response({
            "demo": True,
            "message": (
                f"Tip sent with ${redeemed} discovery credit applied."
                if redeemed > Decimal("0.00")
                else "Tip sent."
            ),
            "tip": serialize_tip(tip),
            "email_shared": bool(contact and contact.email_shared),
            "discovery_credits_applied": str(redeemed.quantize(Decimal("0.01"))),
            "wallet_balance": str(wallet_balance(request.user).quantize(Decimal("0.01"))),
        }, status=status.HTTP_201_CREATED)

    if not stripe_ready():
        return Response({"error": "Stripe is not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    session, checkout_error = create_tip_checkout_session(
        request.user,
        artist,
        profession,
        amount,
        message=message,
        share_email=share_email,
        referral_source=referral_source,
    )
    if checkout_error:
        return Response({"error": checkout_error}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "checkout_url": session.url,
        "checkout_session_id": session.id,
    })


@api_view(["POST"])
def subscribe_to_artist(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if not settings.DEBUG:
        return Response(
            {"error": "Direct subscribe is disabled in production. Use checkout instead."},
            status=status.HTTP_403_FORBIDDEN,
        )

    billing_date, billing_date_error = parse_billing_date(request.data.get("billing_date", 1))
    if billing_date_error:
        return Response({"error": billing_date_error}, status=status.HTTP_400_BAD_REQUEST)

    artist, artist_error = get_artist_or_error(request.data.get("artist_id"))
    if artist_error:
        return artist_error
    profession, profession_error = get_profession_or_error(artist, request.data.get("profession"))
    if profession_error:
        return profession_error
    tier, monthly_amount, amount_error = get_tier_and_amount(request, artist, profession)
    if amount_error:
        status_code = status.HTTP_404_NOT_FOUND if amount_error == "Support tier not found" else status.HTTP_400_BAD_REQUEST
        return Response({"error": amount_error}, status=status_code)

    if request.user == artist:
        return Response({"error": "You cannot subscribe to yourself"}, status=status.HTTP_400_BAD_REQUEST)

    share_email = request_bool(request.data, "share_email_with_artist", False)
    referral_source = (request.data.get("referral_source") or request.query_params.get("ref") or "").strip()[:80]
    sub, created = FanSubscription.objects.update_or_create(
        fan=request.user,
        artist=artist,
        profession=profession,
        defaults={
            "tier": tier,
            "monthly_amount": monthly_amount,
            "billing_date": billing_date,
            "active": True,
        }
    )
    contact = sync_artist_fan_contact(
        request.user,
        artist,
        source=ArtistFanContact.SUPPORT_PROMPT if share_email else ArtistFanContact.SIGNUP_OPT_IN,
        explicit_share=share_email,
    )
    log_fan_journey_event(
        FanJourneyEvent.SUBSCRIBE,
        artist,
        fan=request.user,
        metadata={
            "profession": profession,
            "monthly_amount": str(sub.monthly_amount),
            "source": "direct_subscribe",
            "referral_source": referral_source,
        },
    )

    return Response({
        "created": created,
        "message": f"{request.user.username} now supports {artist.username}'s {ArtistProfile.profession_label(profession)} for ${sub.monthly_amount}/month",
        "monthly_amount": str(sub.monthly_amount),
        "artist_share": str(sub.artist_share),
        "platform_fee": str(sub.platform_fee),
        "billing_date": sub.billing_date,
        "profession": sub.profession,
        "profession_label": ArtistProfile.profession_label(sub.profession),
        "tier_id": sub.tier_id,
        "tier_name": sub.tier.name if sub.tier else "Supporter",
        "email_shared": bool(contact and contact.email_shared),
    })


@api_view(["POST"])
@throttle_classes([CheckoutRateThrottle])
def create_checkout_session(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    blocked = fan_experience_guard(request)
    if blocked:
        return blocked

    allowed, billing_error = billing_allowed(request.user)
    if not allowed:
        return Response({"error": billing_error}, status=status.HTTP_403_FORBIDDEN)

    artist, artist_error = get_artist_or_error(request.data.get("artist_id"))
    if artist_error:
        return artist_error
    profession, profession_error = get_profession_or_error(artist, request.data.get("profession"))
    if profession_error:
        return profession_error
    tier, monthly_amount, amount_error = get_tier_and_amount(request, artist, profession)
    if amount_error:
        status_code = status.HTTP_404_NOT_FOUND if amount_error == "Support tier not found" else status.HTTP_400_BAD_REQUEST
        return Response({"error": amount_error}, status=status_code)

    if request.user == artist:
        return Response({"error": "You cannot subscribe to yourself"}, status=status.HTTP_400_BAD_REQUEST)
    share_email = request_bool(request.data, "share_email_with_artist", False)
    referral_source = (request.data.get("referral_source") or request.query_params.get("ref") or "").strip()[:80]

    if demo_mode_allowed():
        return create_local_demo_subscription(
            request.user,
            artist,
            profession,
            monthly_amount,
            tier,
            share_email=share_email,
            referral_source=referral_source,
        )

    if stripe is None:
        return Response({"error": "Stripe package is not installed. Run pip install -r requirements.txt."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    if not settings.STRIPE_SECRET_KEY:
        return Response({"error": "Stripe is not configured. Set STRIPE_SECRET_KEY."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    connect_account_id = connect_account_for_artist(artist)
    if not connect_account_id and not settings.DEBUG:
        return Response(
            {"error": "This artist has not completed payout setup yet."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY
    amount_cents = int(monthly_amount * Decimal("100"))
    subscription_data = {
        "metadata": {
            "fan_id": str(request.user.id),
            "artist_id": str(artist.id),
            "profession": profession,
            "tier_id": str(tier.id) if tier else "",
            "monthly_amount": str(monthly_amount),
            "share_email_with_artist": "true" if share_email else "",
            "referral_source": referral_source,
        },
    }
    subscription_data.update(
        subscription_connect_params(monthly_amount, connect_account_id, support_rate_for_artist(artist))
    )

    try:
        checkout_session = build_checkout_session(
            mode="subscription",
            success_url=f"{settings.FRONTEND_URL}/?support=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/?support=cancelled",
            client_reference_id=f"{request.user.id}:{artist.id}:{profession}",
            customer_email=request.user.email or None,
            line_items=[{
                "price_data": {
                    "currency": settings.STRIPE_CURRENCY,
                    "product_data": {
                        "name": f"Support {artist.username}",
                    },
                    "unit_amount": amount_cents,
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }],
            metadata={
                "fan_id": str(request.user.id),
                "artist_id": str(artist.id),
                "profession": profession,
                "tier_id": str(tier.id) if tier else "",
                "monthly_amount": str(monthly_amount),
                "share_email_with_artist": "true" if share_email else "",
                "referral_source": referral_source,
            },
            subscription_data=subscription_data,
        )
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "checkout_url": checkout_session.url,
        "checkout_session_id": checkout_session.id,
    })


@api_view(["POST"])
def create_billing_portal_session(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if stripe is None:
        return Response({"error": "Stripe package is not installed. Run pip install -r requirements.txt."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    if not settings.STRIPE_SECRET_KEY:
        return Response({"error": "Stripe is not configured. Set STRIPE_SECRET_KEY."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    artist_id = request.data.get("artist_id")
    profession = request.data.get("profession") or ArtistProfile.DEFAULT_PROFESSION

    try:
        sub = FanSubscription.objects.get(
            fan=request.user,
            artist_id=artist_id,
            profession=profession,
            active=True,
            payment_provider="stripe",
        )
    except FanSubscription.DoesNotExist:
        return Response({"error": "Active Stripe subscription not found"}, status=status.HTTP_404_NOT_FOUND)

    if not sub.stripe_customer_id:
        return Response({"error": "Stripe customer ID is missing for this subscription"}, status=status.HTTP_400_BAD_REQUEST)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=settings.FRONTEND_URL,
        )
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"portal_url": portal_session.url})


@api_view(["POST"])
def unsubscribe_from_artist(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    artist_id = request.data.get("artist_id")
    profession = request.data.get("profession") or ArtistProfile.DEFAULT_PROFESSION

    try:
        sub = FanSubscription.objects.get(fan=request.user, artist_id=artist_id, profession=profession, active=True)
    except FanSubscription.DoesNotExist:
        return Response({"error": "Active subscription not found"}, status=status.HTTP_404_NOT_FOUND)

    if sub.payment_provider == "stripe" and sub.stripe_subscription_id:
        ok, cancel_error = cancel_stripe_subscription(sub)
        if not ok and not settings.DEBUG:
            return Response({"error": cancel_error or "Could not cancel Stripe subscription."}, status=status.HTTP_400_BAD_REQUEST)

    sub.active = False
    sub.save()
    revoke_artist_fan_contact(request.user, sub.artist)
    log_fan_journey_event(
        FanJourneyEvent.UNSUBSCRIBE,
        sub.artist,
        fan=request.user,
        metadata={"profession": sub.profession, "source": "subscription"},
    )

    return Response({
        "message": f"{sub.fan.username} unsubscribed from {sub.artist.username}",
    })


def activate_stripe_subscription(session):
    metadata = session.get("metadata") or {}
    fan_id = metadata.get("fan_id")
    artist_id = metadata.get("artist_id")
    profession = metadata.get("profession") or ArtistProfile.DEFAULT_PROFESSION
    tier_id = metadata.get("tier_id")
    monthly_amount = Decimal(str(metadata.get("monthly_amount", "1.00")))
    share_email = metadata.get("share_email_with_artist") == "true"
    referral_source = metadata.get("referral_source") or ""

    if not fan_id or not artist_id:
        return

    try:
        fan = User.objects.get(id=fan_id)
        artist = User.objects.get(id=artist_id)
    except User.DoesNotExist:
        return

    tier = None
    if tier_id:
        tier = SupportTier.objects.filter(
            id=tier_id,
            artist=artist,
            profession=profession,
            is_active=True,
        ).first()

    sub, _ = FanSubscription.objects.update_or_create(
        fan=fan,
        artist=artist,
        profession=profession,
        defaults={
            "tier": tier,
            "monthly_amount": monthly_amount,
            "billing_date": 1,
            "active": True,
            "payment_provider": "stripe",
            "stripe_checkout_session_id": session.get("id") or "",
            "stripe_customer_id": session.get("customer") or "",
            "stripe_subscription_id": session.get("subscription") or "",
            "stripe_status": session.get("payment_status") or "active",
        },
    )
    sub.save()
    sync_artist_fan_contact(
        fan,
        artist,
        source=ArtistFanContact.SUPPORT_PROMPT if share_email else ArtistFanContact.SIGNUP_OPT_IN,
        explicit_share=share_email,
    )
    log_fan_journey_event(
        FanJourneyEvent.SUBSCRIBE,
        artist,
        fan=fan,
        metadata={
            "profession": profession,
            "monthly_amount": str(sub.monthly_amount),
            "source": "stripe",
            "referral_source": referral_source,
        },
    )
    notify_subscription_started(
        fan,
        artist,
        profession=profession,
        monthly_amount=str(sub.monthly_amount),
        payment_provider="stripe",
    )


def complete_marketplace_purchase_from_session(session):
    from marketplace.models import Product
    from marketplace.purchase_flow import complete_product_purchase

    metadata = session.get("metadata") or {}
    purchase_type = metadata.get("purchase_type")
    if purchase_type not in {"marketplace", "marketplace_cart"}:
        return

    fan_id = metadata.get("fan_id")
    if not fan_id:
        return

    try:
        fan = User.objects.get(id=fan_id)
    except User.DoesNotExist:
        return

    if purchase_type == "marketplace_cart":
        product_ids = [item for item in (metadata.get("product_ids") or "").split(",") if item]
    else:
        product_id = metadata.get("product_id")
        product_ids = [product_id] if product_id else []

    for product_id in product_ids:
        try:
            product = Product.objects.select_related("artist").get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            continue
        complete_product_purchase(fan, product, payment_provider="stripe")


def activate_tip_from_session(session):
    metadata = session.get("metadata") or {}
    if metadata.get("purchase_type") != "tip":
        return

    fan_id = metadata.get("fan_id")
    artist_id = metadata.get("artist_id")
    profession = metadata.get("profession") or ArtistProfile.DEFAULT_PROFESSION
    amount = Decimal(str(metadata.get("amount", "1.00")))
    share_email = metadata.get("share_email_with_artist") == "true"
    message = metadata.get("message") or ""

    if not fan_id or not artist_id:
        return

    try:
        fan = User.objects.get(id=fan_id)
        artist = User.objects.get(id=artist_id)
    except User.DoesNotExist:
        return

    tip = OneTimeTip.objects.create(
        fan=fan,
        artist=artist,
        profession=profession,
        amount=amount,
        message=message[:240],
        is_public=True,
        payment_provider="stripe",
    )
    sync_artist_fan_contact(
        fan,
        artist,
        source=ArtistFanContact.SUPPORT_PROMPT if share_email else ArtistFanContact.SIGNUP_OPT_IN,
        explicit_share=share_email,
    )
    log_fan_journey_event(
        FanJourneyEvent.TIP,
        artist,
        fan=fan,
        metadata={"profession": profession, "amount": str(tip.amount), "source": "stripe"},
    )


def grant_promotion_credits_from_session(session):
    from promotions.services import purchase_credits

    metadata = session.get("metadata") or {}
    user_id = metadata.get("user_id")
    amount = metadata.get("amount")
    if not user_id or not amount:
        return
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return
    purchase_credits(user, Decimal(str(amount)), description="Stripe credit purchase")


def update_subscription_status(stripe_subscription):
    stripe_subscription_id = stripe_subscription.get("id")
    stripe_status = stripe_subscription.get("status", "")

    if not stripe_subscription_id:
        return

    active = stripe_status in {"active", "trialing"}
    previous_status = None

    for sub in FanSubscription.objects.filter(
        stripe_subscription_id=stripe_subscription_id,
        payment_provider="stripe",
    ).select_related("fan", "artist"):
        previous_status = sub.stripe_status
        sub.active = active
        sub.stripe_status = stripe_status
        sub.save(update_fields=["active", "stripe_status"])

        if stripe_status in {"past_due", "unpaid"} and previous_status not in {"past_due", "unpaid"}:
            notify_payment_failed(sub)


def handle_invoice_payment_failed(invoice):
    stripe_subscription_id = invoice.get("subscription")
    if not stripe_subscription_id:
        return

    for sub in FanSubscription.objects.filter(
        stripe_subscription_id=stripe_subscription_id,
        payment_provider="stripe",
    ).select_related("fan", "artist"):
        if sub.stripe_status not in {"past_due", "unpaid"}:
            sub.stripe_status = "past_due"
            sub.save(update_fields=["stripe_status"])
            notify_payment_failed(sub)


@csrf_exempt
@api_view(["POST"])
def stripe_webhook(request):
    if stripe is None:
        return Response({"error": "Stripe package is not installed"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    if not settings.DEBUG and not settings.STRIPE_WEBHOOK_SECRET:
        logger.error("Stripe webhook rejected: STRIPE_WEBHOOK_SECRET is not configured")
        return Response({"error": "Webhook secret not configured"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    payload = request.body
    signature = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        if settings.STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )
        else:
            event = request.data
    except Exception as exc:
        logger.warning("Stripe webhook signature verification failed: %s", exc)
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    event_type = event.get("type")
    event_object = event.get("data", {}).get("object", {})
    logger.info("Stripe webhook received: %s", event_type)

    if event_type == "checkout.session.completed":
        metadata = event_object.get("metadata") or {}
        if metadata.get("purchase_type") in {"marketplace", "marketplace_cart"}:
            complete_marketplace_purchase_from_session(event_object)
        elif metadata.get("purchase_type") == "promotion_credits":
            grant_promotion_credits_from_session(event_object)
        elif metadata.get("purchase_type") == "artist_plan":
            from accounts.artist_plan_stripe import activate_artist_plan_from_session

            activate_artist_plan_from_session(event_object)
        elif metadata.get("purchase_type") == "tip":
            activate_tip_from_session(event_object)
        else:
            activate_stripe_subscription(event_object)

    if event_type in {"customer.subscription.updated", "customer.subscription.deleted"}:
        metadata = event_object.get("metadata") or {}
        if metadata.get("purchase_type") == "artist_plan" or metadata.get("plan") in {"pro", "studio"}:
            from accounts.artist_plan_stripe import sync_artist_plan_subscription

            sync_artist_plan_subscription(event_object)
        else:
            update_subscription_status(event_object)

    if event_type == "invoice.payment_failed":
        handle_invoice_payment_failed(event_object)

    if event_type == "charge.refunded":
        logger.info("Charge refunded: %s", event_object.get("id"))

    return Response({"received": True})


@api_view(["POST"])
def admin_refund(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if not request.user.is_staff:
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    charge_id = (request.data.get("charge_id") or "").strip()
    if not charge_id:
        return Response({"error": "charge_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    amount_cents = request.data.get("amount_cents")
    refund, error = refund_charge(charge_id, amount_cents=int(amount_cents) if amount_cents else None)
    if error:
        return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "message": "Refund processed.",
        "refund_id": refund.id,
        "status": refund.status,
    })
