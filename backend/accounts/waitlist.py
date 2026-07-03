import secrets

from django.conf import settings
from django.utils import timezone

from config.transactional_email import build_waitlist_confirmation_email, send_platform_email

from .models import FanWaitlistEntry


def generate_waitlist_token():
    return secrets.token_urlsafe(32)


def send_waitlist_confirmation(entry):
    token = generate_waitlist_token()
    entry.confirmation_token = token
    entry.confirmed = False
    entry.updated_at = timezone.now()
    entry.save(update_fields=["confirmation_token", "confirmed", "updated_at"])

    frontend_url = (settings.FRONTEND_URL or "http://localhost:5173").rstrip("/")
    confirm_url = f"{frontend_url}/?waitlist-confirm={token}"
    subject, body = build_waitlist_confirmation_email(confirm_url)

    try:
        send_platform_email(subject=subject, body=body, recipient_list=[entry.email])
        return True
    except Exception:
        entry.confirmed = True
        entry.confirmation_token = ""
        entry.save(update_fields=["confirmed", "confirmation_token", "updated_at"])
        return False


def confirm_waitlist_token(token):
    if not token:
        return None, "Confirmation token is required."

    try:
        entry = FanWaitlistEntry.objects.get(confirmation_token=token)
    except FanWaitlistEntry.DoesNotExist:
        return None, "Invalid or expired confirmation link."

    entry.confirmed = True
    entry.confirmation_token = ""
    entry.updated_at = timezone.now()
    entry.save(update_fields=["confirmed", "confirmation_token", "updated_at"])
    return entry, None
