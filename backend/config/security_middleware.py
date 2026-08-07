from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        # Public artist embed widgets are meant to be iframed on external sites.
        is_embed = "/embed/" in (request.path or "")
        if is_embed:
            if "X-Frame-Options" in response:
                del response["X-Frame-Options"]
            response["Content-Security-Policy"] = "frame-ancestors *"
        else:
            if not response.get("X-Frame-Options"):
                response["X-Frame-Options"] = "DENY"
            if getattr(settings, "CONTENT_SECURITY_POLICY", ""):
                response.setdefault("Content-Security-Policy", settings.CONTENT_SECURITY_POLICY)
        return response
