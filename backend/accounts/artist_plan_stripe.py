from decimal import Decimal

from config.platform_fees import ARTIST_PRO_PLANS, STUDIO_PLAN_MONTHLY_CREDITS


def paid_artist_plan_ids():
    return {plan["id"] for plan in ARTIST_PRO_PLANS}


def get_artist_plan_config(plan_id):
    for plan in ARTIST_PRO_PLANS:
        if plan["id"] == plan_id:
            return plan
    return None


def activate_artist_plan(user, plan_id, *, customer_id="", subscription_id=""):
    """Apply a paid artist plan and grant Studio credits when applicable."""
    from promotions.services import maybe_grant_studio_monthly_credits, wallet_balance

    user.artist_plan = plan_id
    update_fields = ["artist_plan"]
    if customer_id:
        user.stripe_artist_customer_id = customer_id
        update_fields.append("stripe_artist_customer_id")
    if subscription_id:
        user.stripe_artist_subscription_id = subscription_id
        update_fields.append("stripe_artist_subscription_id")
    user.save(update_fields=update_fields)

    grant = None
    balance = None
    if plan_id == "studio":
        grant = maybe_grant_studio_monthly_credits(user)
        balance = wallet_balance(user)
    return grant, balance


def deactivate_artist_plan(user):
    user.artist_plan = "free"
    user.stripe_artist_subscription_id = ""
    user.save(update_fields=["artist_plan", "stripe_artist_subscription_id"])


def activate_artist_plan_from_session(session):
    from django.contrib.auth import get_user_model

    metadata = session.get("metadata") or {}
    user_id = metadata.get("user_id")
    plan_id = metadata.get("plan")
    if not user_id or plan_id not in paid_artist_plan_ids():
        return None

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id, user_type=User.ARTIST)
    except User.DoesNotExist:
        return None

    activate_artist_plan(
        user,
        plan_id,
        customer_id=session.get("customer") or "",
        subscription_id=session.get("subscription") or "",
    )
    return user


def sync_artist_plan_subscription(stripe_subscription):
    from django.contrib.auth import get_user_model

    subscription_id = stripe_subscription.get("id")
    status = stripe_subscription.get("status", "")
    metadata = stripe_subscription.get("metadata") or {}
    plan_id = metadata.get("plan")

    if not subscription_id:
        return None

    User = get_user_model()
    user = User.objects.filter(stripe_artist_subscription_id=subscription_id).first()
    if user is None and metadata.get("user_id"):
        try:
            user = User.objects.get(id=metadata["user_id"], user_type=User.ARTIST)
        except User.DoesNotExist:
            return None

    if user is None:
        return None

    if status in {"active", "trialing"} and plan_id in paid_artist_plan_ids():
        activate_artist_plan(
            user,
            plan_id,
            customer_id=stripe_subscription.get("customer") or user.stripe_artist_customer_id,
            subscription_id=subscription_id,
        )
        return user

    if status in {"canceled", "unpaid", "incomplete_expired"}:
        deactivate_artist_plan(user)
    return user
