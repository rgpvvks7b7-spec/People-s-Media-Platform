from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from artists.models import ArtistFanContact, ArtistFollow, FanJourneyEvent
from mediahub.models import MusicUpload
from spaces.local_draw import local_supporter_counts, resolve_local_city
from spaces.models import SpaceBooking
from subscriptions.models import FanSubscription, OneTimeTip


def _decimal(value):
    return Decimal(str(value or "0"))


def build_fan_segments(artist):
    active_subscriber_ids = set(
        FanSubscription.objects.filter(artist=artist, active=True).values_list("fan_id", flat=True)
    )
    all_subscriber_ids = set(
        FanSubscription.objects.filter(artist=artist).values_list("fan_id", flat=True)
    )
    tipper_ids = set(
        OneTimeTip.objects.filter(artist=artist).values_list("fan_id", flat=True)
    )
    purchaser_ids = set(
        FanJourneyEvent.objects.filter(
            artist=artist,
            event_type=FanJourneyEvent.PURCHASE,
        ).values_list("fan_id", flat=True)
    )
    follower_ids = set(
        ArtistFollow.objects.filter(artist=artist).values_list("fan_id", flat=True)
    )
    email_opt_in_ids = set(
        ArtistFanContact.objects.filter(
            artist=artist,
            email_shared=True,
        ).values_list("fan_id", flat=True)
    )

    lapsed_ids = all_subscriber_ids - active_subscriber_ids
    subscribers_only = active_subscriber_ids - tipper_ids - purchaser_ids
    buyers_not_subscribed = (tipper_ids | purchaser_ids) - active_subscriber_ids
    followers_not_converted = follower_ids - active_subscriber_ids - tipper_ids - purchaser_ids

    return [
        {
            "key": "active_subscribers",
            "label": "Active subscribers",
            "count": len(active_subscriber_ids),
        },
        {
            "key": "lapsed_subscribers",
            "label": "Lapsed subscribers",
            "count": len(lapsed_ids),
        },
        {
            "key": "buyers_not_subscribed",
            "label": "Buyers not subscribed",
            "count": len(buyers_not_subscribed),
        },
        {
            "key": "followers_not_converted",
            "label": "Followers not converted",
            "count": len(followers_not_converted),
        },
        {
            "key": "subscribers_only",
            "label": "Subscribers only",
            "count": len(subscribers_only),
        },
        {
            "key": "email_opt_in",
            "label": "Email opt-in supporters",
            "count": len(email_opt_in_ids),
        },
    ]


def build_content_conversion_insights(artist):
    tracks = []
    for track in MusicUpload.objects.filter(artist=artist).order_by("-created_at")[:12]:
        preview_count = FanJourneyEvent.objects.filter(
            artist=artist,
            music_upload=track,
            event_type=FanJourneyEvent.MUSIC_PREVIEW,
        ).count()
        full_count = FanJourneyEvent.objects.filter(
            artist=artist,
            music_upload=track,
            event_type=FanJourneyEvent.MUSIC_FULL_PLAY,
        ).count()
        converted = 0
        first_listens = {}
        for event in FanJourneyEvent.objects.filter(
            artist=artist,
            music_upload=track,
            event_type__in=[FanJourneyEvent.MUSIC_PREVIEW, FanJourneyEvent.MUSIC_FULL_PLAY],
            fan__isnull=False,
        ).order_by("fan_id", "occurred_at"):
            first_listens.setdefault(event.fan_id, event.occurred_at)
        for fan_id, first_listen_at in first_listens.items():
            if FanJourneyEvent.objects.filter(
                artist=artist,
                fan_id=fan_id,
                event_type=FanJourneyEvent.SUBSCRIBE,
                occurred_at__gte=first_listen_at,
                occurred_at__lte=first_listen_at + timezone.timedelta(days=7),
            ).exists():
                converted += 1
        plays = preview_count + full_count
        tracks.append({
            "track_id": track.id,
            "title": track.title,
            "preview_plays": preview_count,
            "full_plays": full_count,
            "subscriber_conversions_7d": converted,
            "conversion_rate": round((converted / plays) * 100, 2) if plays else 0,
        })

    tracks.sort(key=lambda item: (item["subscriber_conversions_7d"], item["conversion_rate"]), reverse=True)
    top = tracks[0] if tracks else None
    suggestions = []
    if top and top["subscriber_conversions_7d"] > 0:
        suggestions.append(
            f"\"{top['title']}\" drove {top['subscriber_conversions_7d']} new subscriber(s) within 7 days of first listen."
        )
    elif tracks:
        suggestions.append("No track has converted listeners to subscribers yet. Try supporter-only previews with a clear subscribe CTA.")
    else:
        suggestions.append("Upload music with preview → supporter access to start measuring conversion.")

    return {
        "tracks": tracks[:6],
        "top_converting_track": top,
        "suggestions": suggestions,
    }


def build_mrr_forecast(artist):
    now = timezone.now()
    start_30d = now - timezone.timedelta(days=30)
    start_60d = now - timezone.timedelta(days=60)

    current_mrr = FanSubscription.objects.filter(
        artist=artist,
        active=True,
    ).aggregate(total=Sum("monthly_amount"))["total"] or Decimal("0.00")

    new_last_30 = FanSubscription.objects.filter(
        artist=artist,
        active=True,
        started_at__gte=start_30d,
    ).aggregate(total=Sum("monthly_amount"))["total"] or Decimal("0.00")

    new_prev_30 = FanSubscription.objects.filter(
        artist=artist,
        active=True,
        started_at__gte=start_60d,
        started_at__lt=start_30d,
    ).aggregate(total=Sum("monthly_amount"))["total"] or Decimal("0.00")

    growth_delta = _decimal(new_last_30) - _decimal(new_prev_30)
    projected_30d = _decimal(current_mrr) + growth_delta
    if growth_delta > 0:
        trend = "up"
        message = f"MRR trending up by ${growth_delta:.2f}/mo based on recent subscriber growth."
    elif growth_delta < 0:
        trend = "down"
        message = f"MRR growth slowed by ${abs(growth_delta):.2f}/mo versus the prior 30 days."
    else:
        trend = "flat"
        message = "MRR growth is flat over the last 30 days."

    return {
        "current_mrr": f"{current_mrr:.2f}",
        "projected_mrr_30d": f"{projected_30d:.2f}",
        "growth_delta_30d": f"{growth_delta:.2f}",
        "trend": trend,
        "message": message,
    }


def build_local_gig_insights(artist, profile):
    city = resolve_local_city(profile.city if profile else "")
    if not city:
        return {
            "local_supporters": 0,
            "notifyable_local_supporters": 0,
            "upcoming_gigs": 0,
            "message": "Add your city to unlock local gig insights.",
        }

    local_counts = local_supporter_counts(artist, city)
    upcoming_gigs = SpaceBooking.objects.filter(
        artist=artist,
        status=SpaceBooking.CONFIRMED,
        starts_at__gte=timezone.now(),
    ).count()

    message = f"{local_counts['local_supporters']} local supporter(s) in {city}."
    if local_counts["notifyable_local_supporters_count"]:
        message += f" You can notify {local_counts['notifyable_local_supporters_count']} opted-in local contact(s) about gigs."

    return {
        "city": city,
        "local_supporters": local_counts["local_supporters"],
        "notifyable_local_supporters": local_counts["notifyable_local_supporters_count"],
        "upcoming_gigs": upcoming_gigs,
        "message": message,
    }


def build_pro_insights(artist):
    profile = getattr(artist, "artist_profile", None)
    return {
        "segments": build_fan_segments(artist),
        "content_conversion": build_content_conversion_insights(artist),
        "mrr_forecast": build_mrr_forecast(artist),
        "local_gigs": build_local_gig_insights(artist, profile),
        "generated_at": timezone.now(),
    }
