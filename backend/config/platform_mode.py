"""Platform launch mode: prelaunch (creators only) vs live (full fan experience)."""

from django.conf import settings

PLATFORM_MODE_LIVE = "live"
PLATFORM_MODE_PRELAUNCH = "prelaunch"

CREATOR_USER_TYPES = frozenset({"artist", "host", "admin"})


def normalize_platform_mode(value):
    if (value or "").strip().lower() == PLATFORM_MODE_PRELAUNCH:
        return PLATFORM_MODE_PRELAUNCH
    return PLATFORM_MODE_LIVE


def is_prelaunch():
    return settings.PLATFORM_MODE == PLATFORM_MODE_PRELAUNCH


def fan_registration_allowed():
    return not is_prelaunch()


def fan_experience_allowed(user):
    if not is_prelaunch():
        return True
    if user and getattr(user, "is_authenticated", False):
        if getattr(user, "is_staff", False):
            return True
        return getattr(user, "user_type", "") in CREATOR_USER_TYPES
    return False


def platform_mode_payload():
    prelaunch = is_prelaunch()
    return {
        "platform_mode": settings.PLATFORM_MODE,
        "fan_registration_open": not prelaunch,
        "fan_experience_open": not prelaunch,
    }


def prelaunch_fan_block_response():
    from rest_framework.response import Response
    from rest_framework import status

    return Response(
        {
            "error": "Fan features open at public launch. Artists and hosts can sign up and set up now.",
            "code": "prelaunch_fan_gated",
            **platform_mode_payload(),
        },
        status=status.HTTP_403_FORBIDDEN,
    )


def fan_experience_guard(request):
    user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
    if fan_experience_allowed(user):
        return None
    return prelaunch_fan_block_response()
