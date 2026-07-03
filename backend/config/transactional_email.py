"""Shared helpers for IndieFund transactional email."""

from django.conf import settings
from django.core.mail import send_mail


def email_delivery_configured():
    backend = settings.EMAIL_BACKEND or ""
    if "console" in backend and not settings.DEBUG:
        return False
    if "smtp" in backend:
        return bool(settings.EMAIL_HOST and settings.DEFAULT_FROM_EMAIL)
    return "console" not in backend


def send_platform_email(*, subject, body, recipient_list, fail_silently=False):
    return send_mail(
        subject=subject[:988],
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        fail_silently=fail_silently,
    )


def build_verification_email(user, verify_url):
    subject = "Verify your IndieFund email"
    body = (
        f"Hi {user.display_name or user.username},\n\n"
        "Please verify your email address to unlock billing, purchases, and receipts on IndieFund.\n\n"
        f"Verify: {verify_url}\n\n"
        "If you did not create this account, you can ignore this email."
    )
    return subject, body


def build_waitlist_confirmation_email(confirm_url):
    subject = "Confirm your IndieFund launch waitlist spot"
    body = (
        "Thanks for joining the IndieFund fan waitlist.\n\n"
        "Confirm your email so we can notify you when Discover, Listen, and support open at launch:\n\n"
        f"{confirm_url}\n\n"
        "If you did not request this, you can ignore this email."
    )
    return subject, body


def build_ticket_receipt_email(fan, product, receipt, show_url):
    subject = f"Ticket confirmed: {product.title}"
    body = (
        f"Hi {fan.display_name or fan.username},\n\n"
        f"Your ticket is confirmed.\n\n"
        f"Item: {product.title}\n"
        f"Amount: ${receipt.get('amount', product.price)}\n"
    )
    show = receipt.get("show") or {}
    if show:
        body += (
            f"Show: {show.get('stage_name', product.artist.username)} @ {show.get('venue_name', 'venue')}\n"
            f"When: {show.get('starts_at')}\n"
            f"City: {show.get('venue_city', '')}\n"
            f"\nAt the door, staff will give you a check-in code. Open My Scene and tap I'm here to enter it.\n"
            f"\nView your ticket in My Scene: {show_url}\n"
        )
    body += "\nYou are receiving this because you registered with this email on IndieFund."
    return subject, body
