from collections import Counter

from artists.business_health import get_artist_business_health
from artists.models import ArtistFollow, ArtistProfile
from subscriptions.models import FanSubscription


def get_fans_also_support(artist_user, request, limit=5):
    """Artists that share the most followers/supporters with this artist."""
    follow_fan_ids = set(
        ArtistFollow.objects.filter(artist=artist_user).values_list("fan_id", flat=True)
    )
    sub_fan_ids = set(
        FanSubscription.objects.filter(artist=artist_user, active=True).values_list("fan_id", flat=True)
    )
    fan_ids = follow_fan_ids | sub_fan_ids
    if not fan_ids:
        return []

    overlap = Counter()
    for artist_id in ArtistFollow.objects.filter(fan_id__in=fan_ids).exclude(artist=artist_user).values_list(
        "artist_id", flat=True
    ):
        overlap[artist_id] += 1
    for artist_id in FanSubscription.objects.filter(
        fan_id__in=fan_ids, active=True
    ).exclude(artist=artist_user).values_list("artist_id", flat=True):
        overlap[artist_id] += 2

    results = []
    for artist_id, score in overlap.most_common(limit * 3):
        try:
            profile = ArtistProfile.objects.select_related("owner").get(owner_id=artist_id)
        except ArtistProfile.DoesNotExist:
            continue
        if profile.on_hiatus:
            continue
        business_health = get_artist_business_health(profile.owner, profile)
        results.append({
            "owner_id": artist_id,
            "owner_username": profile.owner.username,
            "stage_name": profile.stage_name,
            "genre": profile.genre,
            "city": profile.city,
            "hero_image": request.build_absolute_uri(profile.hero_image.url) if profile.hero_image else None,
            "is_verified": profile.is_verified,
            "overlap_score": score,
            "supporter_count": business_health.get("active_subscribers", 0),
            "is_emerging": business_health.get("is_emerging", False),
        })
        if len(results) >= limit:
            break
    return results
