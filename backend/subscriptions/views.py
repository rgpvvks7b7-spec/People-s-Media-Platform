from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import FanSubscription

try:
    import stripe
except ImportError:
    stripe = None

User = get_user_model()


def parse_monthly_amount(value):
    try:
        monthly_amount = Decimal(str(value or "1.00"))
    except (InvalidOperation, ValueError):
        return None, "Monthly amount must be a valid number."

    if monthly_amount < Decimal("1.00"):
        monthly_amount = Decimal("1.00")

    return monthly_amount, ""


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


def create_local_demo_subscription(fan, artist, monthly_amount):
    sub, created = FanSubscription.objects.update_or_create(
        fan=fan,
        artist=artist,
        defaults={
            "monthly_amount": monthly_amount,
            "billing_date": 1,
            "active": True,
            "payment_provider": "demo",
            "stripe_status": "active",
        },
    )

    return Response({
        "created": created,
        "demo": True,
        "message": f"Demo support active: {fan.username} supports {artist.username} for ${sub.monthly_amount}/month.",
        "monthly_amount": str(sub.monthly_amount),
        "artist_share": str(sub.artist_share),
        "platform_fee": str(sub.platform_fee),
    })

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
        subs = subs.filter(artist=request.user)
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


@api_view(["POST"])
def subscribe_to_artist(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    monthly_amount, amount_error = parse_monthly_amount(request.data.get("monthly_amount", "1.00"))
    if amount_error:
        return Response({"error": amount_error}, status=status.HTTP_400_BAD_REQUEST)

    billing_date, billing_date_error = parse_billing_date(request.data.get("billing_date", 1))
    if billing_date_error:
        return Response({"error": billing_date_error}, status=status.HTTP_400_BAD_REQUEST)

    artist, artist_error = get_artist_or_error(request.data.get("artist_id"))
    if artist_error:
        return artist_error

    if request.user == artist:
        return Response({"error": "You cannot subscribe to yourself"}, status=status.HTTP_400_BAD_REQUEST)

    sub, created = FanSubscription.objects.update_or_create(
        fan=request.user,
        artist=artist,
        defaults={
            "monthly_amount": monthly_amount,
            "billing_date": billing_date,
            "active": True,
        }
    )

    return Response({
        "created": created,
        "message": f"{request.user.username} now supports {artist.username} for ${sub.monthly_amount}/month",
        "monthly_amount": str(sub.monthly_amount),
        "artist_share": str(sub.artist_share),
        "platform_fee": str(sub.platform_fee),
        "billing_date": sub.billing_date,
    })


@api_view(["POST"])
def create_checkout_session(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    monthly_amount, amount_error = parse_monthly_amount(request.data.get("monthly_amount", "1.00"))
    if amount_error:
        return Response({"error": amount_error}, status=status.HTTP_400_BAD_REQUEST)

    artist, artist_error = get_artist_or_error(request.data.get("artist_id"))
    if artist_error:
        return artist_error

    if request.user == artist:
        return Response({"error": "You cannot subscribe to yourself"}, status=status.HTTP_400_BAD_REQUEST)

    if settings.DEBUG and (stripe is None or not settings.STRIPE_SECRET_KEY):
        return create_local_demo_subscription(request.user, artist, monthly_amount)

    if stripe is None:
        return Response({"error": "Stripe package is not installed. Run pip install -r requirements.txt."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    if not settings.STRIPE_SECRET_KEY:
        return Response({"error": "Stripe is not configured. Set STRIPE_SECRET_KEY."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    stripe.api_key = settings.STRIPE_SECRET_KEY
    amount_cents = int(monthly_amount * Decimal("100"))

    try:
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            success_url=f"{settings.FRONTEND_URL}/?support=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/?support=cancelled",
            client_reference_id=f"{request.user.id}:{artist.id}",
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
                "monthly_amount": str(monthly_amount),
            },
            subscription_data={
                "metadata": {
                    "fan_id": str(request.user.id),
                    "artist_id": str(artist.id),
                    "monthly_amount": str(monthly_amount),
                },
            },
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

    try:
        sub = FanSubscription.objects.get(
            fan=request.user,
            artist_id=artist_id,
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

    try:
        sub = FanSubscription.objects.get(fan=request.user, artist_id=artist_id, active=True)
    except FanSubscription.DoesNotExist:
        return Response({"error": "Active subscription not found"}, status=status.HTTP_404_NOT_FOUND)

    sub.active = False
    sub.save()

    return Response({
        "message": f"{sub.fan.username} unsubscribed from {sub.artist.username}",
    })


def activate_stripe_subscription(session):
    metadata = session.get("metadata") or {}
    fan_id = metadata.get("fan_id")
    artist_id = metadata.get("artist_id")
    monthly_amount = Decimal(str(metadata.get("monthly_amount", "1.00")))

    if not fan_id or not artist_id:
        return

    try:
        fan = User.objects.get(id=fan_id)
        artist = User.objects.get(id=artist_id)
    except User.DoesNotExist:
        return

    sub, _ = FanSubscription.objects.update_or_create(
        fan=fan,
        artist=artist,
        defaults={
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


def update_subscription_status(stripe_subscription):
    stripe_subscription_id = stripe_subscription.get("id")
    stripe_status = stripe_subscription.get("status", "")

    if not stripe_subscription_id:
        return

    active = stripe_status in {"active", "trialing"}

    FanSubscription.objects.filter(
        stripe_subscription_id=stripe_subscription_id,
        payment_provider="stripe",
    ).update(
        active=active,
        stripe_status=stripe_status,
    )


@csrf_exempt
@api_view(["POST"])
def stripe_webhook(request):
    if stripe is None:
        return Response({"error": "Stripe package is not installed"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

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
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    event_type = event.get("type")
    event_object = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        activate_stripe_subscription(event_object)

    if event_type in {"customer.subscription.updated", "customer.subscription.deleted"}:
        update_subscription_status(event_object)

    return Response({"received": True})
