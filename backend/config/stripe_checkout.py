import logging
import os
from decimal import Decimal

from django.conf import settings

from config.platform_fees import (
    MARKETPLACE_PLATFORM_RATE,
    SUPPORT_PLATFORM_RATE,
    TIP_PLATFORM_RATE,
    split_amount,
)

logger = logging.getLogger("indiefund.stripe")

try:
    import stripe
except ImportError:
    stripe = None


def stripe_ready():
    return stripe is not None and bool(settings.STRIPE_SECRET_KEY)


def demo_mode_allowed():
    if not settings.DEBUG:
        return False
    force_stripe = os.getenv("FORCE_STRIPE_CHECKOUT", "").strip().lower() in {"1", "true", "yes", "on"}
    return not force_stripe


def application_fee_cents(amount, platform_rate):
    _, platform_fee = split_amount(amount, platform_rate)
    return int(platform_fee * Decimal("100"))


def connect_account_for_artist(artist):
    profile = getattr(artist, "artist_profile", None)
    if not profile:
        return None
    account_id = profile.stripe_connect_account_id
    if not account_id:
        return None
    if profile.stripe_connect_onboarded_at:
        return account_id
    return account_id if settings.DEBUG else None


def checkout_payment_intent_data(amount, platform_rate, connect_account_id, *, host_share=None):
    _, platform_fee = split_amount(amount, platform_rate)
    host_share = Decimal(str(host_share or "0"))
    application_fee = (platform_fee + host_share).quantize(Decimal("0.01"))
    return checkout_payment_intent_data_with_fees(application_fee, connect_account_id)


def checkout_payment_intent_data_with_fees(application_fee, connect_account_id):
    fee_cents = int(Decimal(str(application_fee)).quantize(Decimal("0.01")) * Decimal("100"))
    data = {"application_fee_amount": fee_cents}
    if connect_account_id:
        data["transfer_data"] = {"destination": connect_account_id}
    return data


def subscription_connect_params(amount, connect_account_id):
    fee_cents = application_fee_cents(amount, SUPPORT_PLATFORM_RATE)
    params = {}
    if connect_account_id:
        params["transfer_data"] = {"destination": connect_account_id}
        params["application_fee_percent"] = float(SUPPORT_PLATFORM_RATE * Decimal("100"))
    return params


def automatic_tax_params():
    if getattr(settings, "STRIPE_AUTOMATIC_TAX", True) and not settings.DEBUG:
        return {"automatic_tax": {"enabled": True}}
    return {}


def build_checkout_session(**kwargs):
    kwargs.update(automatic_tax_params())
    return stripe.checkout.Session.create(**kwargs)


def cancel_stripe_subscription(subscription):
    if not stripe_ready() or not subscription.stripe_subscription_id:
        return False, "No Stripe subscription to cancel."

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        stripe.Subscription.cancel(subscription.stripe_subscription_id)
        return True, ""
    except Exception as exc:
        logger.exception("Failed to cancel Stripe subscription %s", subscription.stripe_subscription_id)
        return False, str(exc)


def create_tip_checkout_session(fan, artist, profession, amount, message="", share_email=False, referral_source=""):
    connect_account_id = connect_account_for_artist(artist)
    if stripe_ready() and not connect_account_id and not settings.DEBUG:
        return None, "Artist has not completed payout setup."

    amount_cents = int(amount * Decimal("100"))
    metadata = {
        "purchase_type": "tip",
        "fan_id": str(fan.id),
        "artist_id": str(artist.id),
        "profession": profession,
        "amount": str(amount),
        "message": message[:240],
        "share_email_with_artist": "true" if share_email else "",
        "referral_source": referral_source,
    }

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session_kwargs = {
        "mode": "payment",
        "success_url": f"{settings.FRONTEND_URL}/?tip=success&session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{settings.FRONTEND_URL}/?tip=cancelled",
        "customer_email": fan.email or None,
        "line_items": [{
            "price_data": {
                "currency": settings.STRIPE_CURRENCY,
                "product_data": {"name": f"Tip for {artist.username}"},
                "unit_amount": amount_cents,
            },
            "quantity": 1,
        }],
        "metadata": metadata,
        "payment_intent_data": checkout_payment_intent_data(amount, TIP_PLATFORM_RATE, connect_account_id),
    }
    session = build_checkout_session(**session_kwargs)
    return session, ""


def refund_charge(charge_id, amount_cents=None):
    if not stripe_ready():
        return None, "Stripe is not configured."

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        params = {"charge": charge_id}
        if amount_cents:
            params["amount"] = amount_cents
        refund = stripe.Refund.create(**params)
        return refund, ""
    except Exception as exc:
        logger.exception("Refund failed for charge %s", charge_id)
        return None, str(exc)
