from django.contrib.auth import get_user_model
from django.utils import timezone

from artists.models import ArtistFanContact
from spaces.local_draw import resolve_local_city
from subscriptions.models import FanSubscription

from .email_delivery import send_gig_alert_email
from .models import Notification


User = get_user_model()

REMINDER_COOLDOWN_HOURS = 48


def gig_target_url(booking_id):
    return f"/?page=my-scene&show={booking_id}"


def gig_notification_title(booking):
    stage_name = getattr(getattr(booking.artist, "artist_profile", None), "stage_name", booking.artist.username)
    return f"{stage_name} live at {booking.listing.name}"


def gig_notification_body(booking):
    return (
        f"{booking.starts_at:%a, %b %-d · %-I:%M %p} · {booking.listing.city}"
        f"{' · bar open' if booking.listing.bar_open else ''}"
    )


def local_subscriber_fans(artist, city):
    city = (city or "").strip()
    if not city:
        return User.objects.none()

    fan_ids = (
        FanSubscription.objects.filter(
            artist=artist,
            active=True,
            fan__is_active=True,
            fan__discovery_location__iexact=city,
        )
        .values_list("fan_id", flat=True)
        .distinct()
    )
    return User.objects.filter(id__in=fan_ids, is_active=True).exclude(id=artist.id)


def email_opted_in_fan_ids(artist, fan_ids):
    if not fan_ids:
        return set()
    return set(
        ArtistFanContact.objects.filter(
            artist=artist,
            fan_id__in=fan_ids,
            email_shared=True,
            fan__is_active=True,
        ).values_list("fan_id", flat=True)
    )


def already_notified_booking(booking_id):
    marker = f"show={booking_id}"
    return Notification.objects.filter(
        notification_type=Notification.GIG,
        target_url__contains=marker,
    ).exists()


def recent_reminder_sent(booking_id):
    since = timezone.now() - timezone.timedelta(hours=REMINDER_COOLDOWN_HOURS)
    marker = f"show={booking_id}"
    return Notification.objects.filter(
        notification_type=Notification.GIG,
        target_url__contains=marker,
        created_at__gte=since,
    ).exists()


def notify_local_supporters_for_booking(booking, *, reminder=False, force=False):
    """
    Notify all active local subscribers (in-app). Email only when fan opted in.
    Auto-notify skips if this booking was already announced unless force=True.
    Manual reminders respect a 48h cooldown unless force=True.
    """
    city = resolve_local_city(booking.listing.city)
    if not city:
        return {
            "notified_count": 0,
            "email_count": 0,
            "skipped": True,
            "reason": "missing_city",
        }

    if not force:
        if reminder and recent_reminder_sent(booking.id):
            return {
                "notified_count": 0,
                "email_count": 0,
                "skipped": True,
                "reason": "reminder_cooldown",
            }
        if not reminder and already_notified_booking(booking.id):
            return {
                "notified_count": 0,
                "email_count": 0,
                "skipped": True,
                "reason": "already_notified",
            }

    fans = list(local_subscriber_fans(booking.artist, city))
    if not fans:
        return {
            "notified_count": 0,
            "email_count": 0,
            "skipped": False,
            "reason": "no_local_subscribers",
        }

    fan_ids = [fan.id for fan in fans]
    email_ids = email_opted_in_fan_ids(booking.artist, fan_ids)
    title = gig_notification_title(booking)
    body = gig_notification_body(booking)
    target_url = gig_target_url(booking.id)
    stage_name = getattr(getattr(booking.artist, "artist_profile", None), "stage_name", booking.artist.username)

    notifications = [
        Notification(
            recipient=fan,
            actor=booking.artist,
            notification_type=Notification.GIG,
            title=title[:180],
            body=body,
            target_url=target_url[:255],
        )
        for fan in fans
    ]
    Notification.objects.bulk_create(notifications)

    email_count = 0
    for fan in fans:
        if fan.id in email_ids:
            if send_gig_alert_email(fan, booking, stage_name):
                email_count += 1

    return {
        "notified_count": len(notifications),
        "email_count": email_count,
        "skipped": False,
        "reason": "",
    }
