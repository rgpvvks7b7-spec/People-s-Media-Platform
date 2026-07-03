"""
Security and configuration audit for beta deploy readiness.

Usage:
  python manage.py beta_security_check
  python manage.py beta_security_check --strict
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts import views as account_views
from config.transactional_email import email_delivery_configured


class Command(BaseCommand):
    help = "Run lightweight security and production-readiness checks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Exit with a non-zero status if any check fails (for CI/deploy gating).",
        )

    def handle(self, *args, **options):
        checks = [
            self.check_secret_key(),
            self.check_debug(),
            self.check_allowed_hosts(),
            self.check_ssl_redirect(),
            self.check_secure_cookies(),
            self.check_hsts(),
            self.check_stripe_webhook(),
            self.check_email_backend(),
            self.check_email_delivery(),
            self.check_throttling(),
            self.check_throttle_rates(),
            self.check_auth_surface_throttles(),
            self.check_upload_throttles(),
            self.check_media_storage(),
            self.check_promotion_invariants(),
        ]
        self.stdout.write("\nSecurity audit:")
        failed = 0
        for name, ok, detail in checks:
            status = self.style.SUCCESS("PASS") if ok else self.style.WARNING("WARN")
            self.stdout.write(f"  [{status}] {name} — {detail}")
            if not ok:
                failed += 1

        if failed:
            self.stdout.write(self.style.WARNING(f"\n{failed} warning(s). Review before production deploy."))
            if options.get("strict"):
                raise CommandError(f"{failed} security check(s) failed under --strict.")
        else:
            self.stdout.write(self.style.SUCCESS("\nAll checks passed for beta deploy."))

    def check_secret_key(self):
        weak = settings.SECRET_KEY in {"", "dev-only-change-this"}
        return ("SECRET_KEY", not weak, "Set a unique SECRET_KEY in production" if weak else "Configured")

    def check_debug(self):
        return ("DEBUG", not settings.DEBUG, "Disable DEBUG in production" if settings.DEBUG else "DEBUG=False")

    def check_allowed_hosts(self):
        hosts = settings.ALLOWED_HOSTS
        ok = settings.DEBUG or (bool(hosts) and "localhost" not in hosts and "*" not in hosts)
        detail = ", ".join(hosts) if hosts else "empty — set ALLOWED_HOSTS for production"
        return ("ALLOWED_HOSTS", ok, detail)

    def check_ssl_redirect(self):
        ok = settings.DEBUG or settings.SECURE_SSL_REDIRECT
        detail = "Enabled" if settings.SECURE_SSL_REDIRECT else "Enable SECURE_SSL_REDIRECT in production"
        return ("HTTPS redirect", ok, detail)

    def check_secure_cookies(self):
        secure = settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE
        ok = settings.DEBUG or secure
        detail = "Session + CSRF cookies are Secure" if secure else "Set SESSION_COOKIE_SECURE and CSRF_COOKIE_SECURE"
        return ("Secure cookies", ok, detail)

    def check_hsts(self):
        ok = settings.DEBUG or settings.SECURE_HSTS_SECONDS > 0
        detail = f"max-age={settings.SECURE_HSTS_SECONDS}" if settings.SECURE_HSTS_SECONDS else "Set SECURE_HSTS_SECONDS for production"
        return ("HSTS", ok, detail)

    def check_stripe_webhook(self):
        ok = bool(settings.STRIPE_WEBHOOK_SECRET) or settings.DEBUG
        return ("STRIPE_WEBHOOK_SECRET", ok, "Set webhook secret for live Stripe" if not ok else "Configured")

    def check_email_backend(self):
        console = "console" in settings.EMAIL_BACKEND
        ok = not console or settings.DEBUG
        return ("EMAIL_BACKEND", ok, settings.EMAIL_BACKEND)

    def check_email_delivery(self):
        ok = settings.DEBUG or email_delivery_configured()
        detail = (
            "SMTP configured for transactional email"
            if ok
            else "Configure SMTP + DEFAULT_FROM_EMAIL; run test_transactional_email on staging"
        )
        return ("Transactional email", ok, detail)

    def check_throttling(self):
        configured = bool(getattr(settings, "REST_FRAMEWORK", {}).get("DEFAULT_THROTTLE_CLASSES"))
        enabled = getattr(settings, "API_THROTTLE_ENABLED", True)
        ok = settings.DEBUG or (configured and enabled)
        detail = (
            "DRF throttles enabled"
            if configured and enabled
            else "Set API_THROTTLE_ENABLED=1 and DRF throttle classes for production"
        )
        return ("API throttling", ok, detail)

    def check_throttle_rates(self):
        rates = getattr(settings, "REST_FRAMEWORK", {}).get("DEFAULT_THROTTLE_RATES", {})
        required = ("auth", "checkout", "upload")
        missing = [scope for scope in required if scope not in rates]
        ok = not missing
        detail = "auth, checkout, upload scopes configured" if ok else f"Missing rates: {', '.join(missing)}"
        return ("Throttle rate scopes", ok, detail)

    def check_auth_surface_throttles(self):
        endpoints = [
            ("register", account_views.register),
            ("login", account_views.login_view),
            ("waitlist", account_views.fan_waitlist_join),
        ]
        missing = []
        for name, view in endpoints:
            throttle_classes = getattr(getattr(view, "cls", None), "throttle_classes", None)
            if not throttle_classes:
                missing.append(name)
        ok = not missing
        detail = "register, login, waitlist throttled" if ok else f"Missing throttle: {', '.join(missing)}"
        return ("Auth surface throttles", ok, detail)

    def check_upload_throttles(self):
        from config.throttling import UploadRateThrottle
        from mediahub import views as media_views
        from spaces import views as space_views

        endpoints = [
            ("create_music", media_views.create_music),
            ("create_artwork", media_views.create_artwork),
            ("space_listings", space_views.listings),
        ]
        missing = []
        for name, view in endpoints:
            throttle_classes = getattr(getattr(view, "cls", None), "throttle_classes", None) or []
            if UploadRateThrottle not in throttle_classes:
                missing.append(name)
        ok = not missing
        detail = "Upload endpoints throttled" if ok else f"Missing upload throttle: {', '.join(missing)}"
        return ("Upload throttles", ok, detail)

    def check_media_storage(self):
        s3 = getattr(settings, "USE_S3_MEDIA", False)
        detail = "S3 private media enabled" if s3 else "Local media (OK for dev)"
        return ("Media storage", True, detail)

    def check_promotion_invariants(self):
        from config.platform_fees import CAMPAIGN_MAX_BUDGET, CAMPAIGN_MAX_ACTIVE, DISCOVERY_ADS_TAGLINE
        from promotions.services import promotion_invariants

        invariants = promotion_invariants()
        ok = (
            invariants["max_budget"] == str(CAMPAIGN_MAX_BUDGET)
            and invariants["max_active"] == CAMPAIGN_MAX_ACTIVE
            and invariants["no_bidding"] is True
            and bool(DISCOVERY_ADS_TAGLINE)
        )
        detail = (
            f"${invariants['max_budget']} cap, {invariants['max_active']} active max, engagement billing"
            if ok
            else "Promotion invariants mismatch — review platform_fees.py"
        )
        return ("Discovery Ads invariants", ok, detail)
