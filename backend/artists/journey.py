from django.db.models import F
from django.utils import timezone

from .models import ArtistJourneyRollup, FanJourneyEvent


def week_start(value):
    return value.date() - timezone.timedelta(days=value.weekday())


def log_fan_journey_event(
    event_type,
    artist,
    fan=None,
    music_upload=None,
    metadata=None,
):
    if not artist or event_type not in dict(FanJourneyEvent.EVENT_TYPES):
        return None

    event = FanJourneyEvent.objects.create(
        fan=fan if getattr(fan, "is_authenticated", False) else None,
        artist=artist,
        event_type=event_type,
        music_upload=music_upload,
        metadata=metadata or {},
    )

    now = timezone.now()
    for period, period_start in (
        (ArtistJourneyRollup.DAILY, now.date()),
        (ArtistJourneyRollup.WEEKLY, week_start(now)),
    ):
        rollup, _ = ArtistJourneyRollup.objects.get_or_create(
            artist=artist,
            period=period,
            period_start=period_start,
            event_type=event_type,
            defaults={"count": 0},
        )
        ArtistJourneyRollup.objects.filter(id=rollup.id).update(count=F("count") + 1)

    try:
        from challenges.services import increment_metric

        metric = None
        if event_type == FanJourneyEvent.SUBSCRIBE:
            metric = "new_subscriber"
        if event_type == FanJourneyEvent.CONTENT_ENGAGEMENT and (metadata or {}).get("engagement_type") == "comment":
            metric = "reply_comments"
        if metric:
            increment_metric(artist, metric, now=now)
    except Exception:
        pass

    return event
