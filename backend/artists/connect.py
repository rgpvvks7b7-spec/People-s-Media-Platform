from django.conf import settings

try:
    import stripe
except ImportError:
    stripe = None


def connect_configured():
    return stripe is not None and bool(settings.STRIPE_SECRET_KEY)


def ensure_connect_account(profile):
    if profile.stripe_connect_account_id:
        return profile.stripe_connect_account_id

    if not connect_configured():
        return ""

    stripe.api_key = settings.STRIPE_SECRET_KEY
    account = stripe.Account.create(
        type="express",
        capabilities={
            "transfers": {"requested": True},
        },
        metadata={
            "artist_user_id": str(profile.owner_id),
            "stage_name": profile.stage_name[:120],
        },
    )
    profile.stripe_connect_account_id = account.id
    profile.save(update_fields=["stripe_connect_account_id"])
    return account.id


def create_connect_onboarding_link(profile):
    account_id = ensure_connect_account(profile)
    if not account_id:
        return None, "Stripe Connect is not configured."

    stripe.api_key = settings.STRIPE_SECRET_KEY
    link = stripe.AccountLink.create(
        account=account_id,
        refresh_url=f"{settings.FRONTEND_URL}/?connect=refresh",
        return_url=f"{settings.FRONTEND_URL}/?connect=return",
        type="account_onboarding",
    )
    return link.url, ""


def fetch_connect_status(profile):
    if not profile.stripe_connect_account_id:
        return {
            "connected": False,
            "account_id": "",
            "charges_enabled": False,
            "payouts_enabled": False,
            "details_submitted": False,
        }

    if not connect_configured():
        return {
            "connected": True,
            "account_id": profile.stripe_connect_account_id,
            "charges_enabled": False,
            "payouts_enabled": False,
            "details_submitted": bool(profile.stripe_connect_onboarded_at),
            "demo_mode": True,
        }

    stripe.api_key = settings.STRIPE_SECRET_KEY
    account = stripe.Account.retrieve(profile.stripe_connect_account_id)
    details_submitted = bool(account.get("details_submitted"))
    payouts_enabled = bool(account.get("payouts_enabled"))

    if details_submitted and payouts_enabled and not profile.stripe_connect_onboarded_at:
        from django.utils import timezone

        profile.stripe_connect_onboarded_at = timezone.now()
        profile.save(update_fields=["stripe_connect_onboarded_at"])

    return {
        "connected": True,
        "account_id": profile.stripe_connect_account_id,
        "charges_enabled": bool(account.get("charges_enabled")),
        "payouts_enabled": payouts_enabled,
        "details_submitted": details_submitted,
    }
