from django.conf import settings
from config.transactional_email import build_ticket_receipt_email, send_platform_email


def send_gig_alert_email(fan, booking, stage_name):
    if not fan.email:
        return False

    frontend_url = (settings.FRONTEND_URL or "http://localhost:5173").rstrip("/")
    show_url = f"{frontend_url}/?page=my-scene&show={booking.id}"
    venue = booking.listing.name
    city = booking.listing.city or ""
    when = booking.starts_at.strftime("%A, %B %-d · %-I:%M %p")

    subject = f"Local gig: {stage_name} at {venue}"
    body = (
        f"Hi {fan.display_name or fan.username},\n\n"
        f"{stage_name} just confirmed a show near you.\n\n"
        f"When: {when}\n"
        f"Where: {venue}, {city}\n"
    )
    if booking.listing.bar_open:
        body += "Bar open during the show.\n"
    if booking.listing.kitchen_open:
        body += "Kitchen open during the show.\n"
    body += (
        f"\nView details: {show_url}\n\n"
        "You are receiving this because you support this artist and opted in to email updates."
    )

    try:
        send_platform_email(
            subject=subject,
            body=body,
            recipient_list=[fan.email],
        )
        return True
    except Exception:
        return False


def send_ticket_receipt_email(fan, product, receipt):
    if not fan.email:
        return False

    frontend_url = (settings.FRONTEND_URL or "http://localhost:5173").rstrip("/")
    show = receipt.get("show") or {}
    show_url = f"{frontend_url}/?page=my-scene&show={show.get('booking_id')}" if show.get("booking_id") else frontend_url
    subject, body = build_ticket_receipt_email(fan, product, receipt, show_url)

    try:
        send_platform_email(
            subject=subject,
            body=body,
            recipient_list=[fan.email],
        )
        return True
    except Exception:
        return False
