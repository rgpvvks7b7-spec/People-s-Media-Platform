"""Fan support-slot limits (default 50 active subscriptions)."""

from rest_framework import status
from rest_framework.response import Response

from .models import FanSubscription

DEFAULT_EXTENSION = 25


def active_subscription_count(fan):
    if not fan or not getattr(fan, "is_authenticated", False):
        return 0
    return FanSubscription.objects.filter(fan=fan, active=True).count()


def subscription_limit_for(fan):
    return int(getattr(fan, "subscription_limit", 50) or 50)


def already_supports(fan, artist, profession):
    return FanSubscription.objects.filter(
        fan=fan,
        artist=artist,
        profession=profession,
        active=True,
    ).exists()


def subscription_limit_block(fan, artist, profession):
    """Return an error Response when a new support slot would exceed the fan limit."""
    if already_supports(fan, artist, profession):
        return None

    limit = subscription_limit_for(fan)
    count = active_subscription_count(fan)
    if count < limit:
        return None

    return Response(
        {
            "error": (
                f"You're supporting {count} of {limit} artists. "
                "Extend your discovery limit to support more."
            ),
            "code": "subscription_limit_reached",
            "count": count,
            "limit": limit,
            "extension_size": DEFAULT_EXTENSION,
        },
        status=status.HTTP_403_FORBIDDEN,
    )


def extend_subscription_limit(fan, *, amount=DEFAULT_EXTENSION):
    amount = max(1, min(int(amount or DEFAULT_EXTENSION), 100))
    fan.subscription_limit = subscription_limit_for(fan) + amount
    fan.save(update_fields=["subscription_limit"])
    return {
        "subscription_limit": fan.subscription_limit,
        "subscription_count": active_subscription_count(fan),
        "extended_by": amount,
    }
