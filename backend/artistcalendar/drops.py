"""Drops: scheduled releases that gate a linked track until drop time.

A drop is a RELEASE calendar item linked to a music upload. Until the drop
moment the track is locked for everyone except the artist; supporters unlock
``supporter_early_hours`` before the public. No background workers — the lock
is evaluated at request time, so the track flips live exactly on schedule.
"""
from datetime import timedelta

from django.utils import timezone

from notifications.models import Notification
from notifications.services import notify_opted_in_supporters
from subscriptions.models import FanSubscription

from .models import ArtistCalendarItem


def upcoming_drop_for_track(track):
    return (
        ArtistCalendarItem.objects
        .filter(
            music_upload=track,
            item_type=ArtistCalendarItem.RELEASE,
            starts_at__gt=timezone.now(),
        )
        .exclude(visibility=ArtistCalendarItem.PRIVATE)
        .order_by("starts_at")
        .first()
    )


def drop_lock_state(track, user):
    """Return None when the track has no pending drop, else the lock state."""
    item = upcoming_drop_for_track(track)
    if item is None:
        return None

    now = timezone.now()
    early_access_at = (
        item.starts_at - timedelta(hours=item.supporter_early_hours)
        if item.supporter_early_hours
        else None
    )

    is_owner = getattr(user, "is_authenticated", False) and user.id == track.artist_id
    is_supporter = False
    if getattr(user, "is_authenticated", False) and not is_owner:
        is_supporter = FanSubscription.objects.filter(
            fan=user,
            artist_id=track.artist_id,
            active=True,
        ).exists()

    supporter_window_open = early_access_at is not None and now >= early_access_at
    unlocked = is_owner or (is_supporter and supporter_window_open)

    return {
        "calendar_item_id": item.id,
        "title": item.title,
        "drop_at": item.starts_at,
        "early_access_at": early_access_at,
        "supporter_early_hours": item.supporter_early_hours,
        "is_supporter": is_supporter,
        "unlocked": unlocked,
        "supporter_window_open": supporter_window_open,
    }


def drop_access_message(state):
    drop_day = state["drop_at"].strftime("%d %b, %H:%M")
    if state["supporter_early_hours"] and not state["is_supporter"]:
        return (
            f"Drops {drop_day}. Supporters unlock it "
            f"{state['supporter_early_hours']} hours early — support to hear it first."
        )
    return f"Drops {drop_day}."


def announce_drop(item):
    """Notify opted-in supporters about a scheduled drop. Returns count sent."""
    drop_day = item.starts_at.strftime("%d %b, %H:%M")
    body = f"Drops {drop_day}."
    if item.supporter_early_hours:
        body = f"{body} You unlock it {item.supporter_early_hours} hours early."
    return notify_opted_in_supporters(
        item.artist,
        Notification.MUSIC,
        title=f"Drop announced: {item.title}"[:180],
        body=body,
        target_url=f"/?artist={item.artist.username}",
    )
