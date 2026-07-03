from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class _ToggleableThrottle:
    """Honour the global API_THROTTLE_ENABLED switch.

    Views apply these throttles explicitly, so without this they would keep
    firing even when throttling is switched off (local dev and tests). Gating on
    the same flag as DEFAULT_THROTTLE_CLASSES keeps behaviour consistent:
    throttling is fully off in DEBUG and on in production.
    """

    def allow_request(self, request, view):
        if not getattr(settings, "API_THROTTLE_ENABLED", True):
            return True
        return super().allow_request(request, view)


class AuthRateThrottle(_ToggleableThrottle, AnonRateThrottle):
    scope = "auth"


class CheckoutRateThrottle(_ToggleableThrottle, UserRateThrottle):
    scope = "checkout"


class PromotionRateThrottle(_ToggleableThrottle, UserRateThrottle):
    scope = "promotion"


class UploadRateThrottle(_ToggleableThrottle, UserRateThrottle):
    scope = "upload"
