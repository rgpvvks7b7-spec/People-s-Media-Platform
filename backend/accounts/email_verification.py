from django.conf import settings
from django.utils import timezone

from config.transactional_email import build_verification_email, send_platform_email
from .models import User


def generate_verification_token():
    import secrets

    return secrets.token_urlsafe(32)


def verification_required(user):
    if settings.DEBUG and not getattr(settings, "REQUIRE_EMAIL_VERIFICATION", False):
        return False
    return not user.email_verified


def send_verification_email(user):
    if not user.email:
        return False

    token = generate_verification_token()
    user.email_verification_token = token
    user.email_verification_sent_at = timezone.now()
    user.save(update_fields=["email_verification_token", "email_verification_sent_at"])

    frontend_url = (settings.FRONTEND_URL or "http://localhost:5173").rstrip("/")
    verify_url = f"{frontend_url}/?verify-email={token}"
    subject, body = build_verification_email(user, verify_url)

    try:
        send_platform_email(subject=subject, body=body, recipient_list=[user.email])
        return True
    except Exception:
        return False


def verify_email_token(token):
    if not token:
        return None, "Verification token is required."

    try:
        user = User.objects.get(email_verification_token=token)
    except User.DoesNotExist:
        return None, "Invalid or expired verification link."

    user.email_verified = True
    user.email_verification_token = ""
    user.save(update_fields=["email_verified", "email_verification_token"])
    return user, None
