from artists.models import ArtistFanContact
from subscriptions.models import FanSubscription


def normalized_city(value):
    return (value or "").strip()


def resolve_local_city(*cities):
    for city in cities:
        resolved = normalized_city(city)
        if resolved:
            return resolved
    return ""


def local_supporter_counts(artist, city):
    city = normalized_city(city)
    if not city:
        return {
            "local_city": "",
            "local_supporters": 0,
            "notifyable_local_supporters_count": 0,
        }

    active_subs = FanSubscription.objects.filter(artist=artist, active=True)
    local_supporters = active_subs.filter(fan__discovery_location__iexact=city).count()
    notifyable = ArtistFanContact.objects.filter(
        artist=artist,
        email_shared=True,
        fan__is_active=True,
        fan__discovery_location__iexact=city,
    ).count()
    return {
        "local_city": city,
        "local_supporters": local_supporters,
        "notifyable_local_supporters_count": notifyable,
    }
