from django.contrib.auth import get_user_model
from django.db.models import Q

from artists.fans_also_support import get_fans_also_support
from artists.models import ArtistProfile

from .models import normalize_genre_terms

User = get_user_model()

MAX_SIMILAR_ARTIST_TARGETS = 5


def _serialize_artist_target(profile, request, *, reason="", overlap_score=0):
    return {
        "owner_id": profile.owner_id,
        "owner_username": profile.owner.username,
        "stage_name": profile.stage_name,
        "genre": profile.genre,
        "city": profile.city,
        "hero_image": request.build_absolute_uri(profile.hero_image.url) if profile.hero_image else None,
        "overlap_score": overlap_score,
        "reason": reason,
    }


def genre_peer_artists(artist_user, request, limit=8):
    """Artists in overlapping genres — useful when co-occurrence data is sparse."""
    try:
        profile = artist_user.artist_profile
    except ArtistProfile.DoesNotExist:
        return []

    terms = normalize_genre_terms(profile.genre)
    if not terms:
        return []

    peers = []
    for peer in (
        ArtistProfile.objects.select_related("owner")
        .exclude(owner=artist_user)
        .filter(on_hiatus=False)
        .order_by("-created_at")[:80]
    ):
        if not (terms & normalize_genre_terms(peer.genre)):
            continue
        peers.append(
            _serialize_artist_target(
                peer,
                request,
                reason="Shared genre",
                overlap_score=len(terms & normalize_genre_terms(peer.genre)),
            )
        )
        if len(peers) >= limit:
            break
    return peers


def similar_artist_suggestions(artist_user, request, limit=8):
    """Blend co-supported artists with genre peers for campaign targeting."""
    merged = {}
    for item in get_fans_also_support(artist_user, request, limit=limit):
        merged[item["owner_id"]] = {
            **item,
            "reason": "Fans also support",
        }

    for item in genre_peer_artists(artist_user, request, limit=limit):
        existing = merged.get(item["owner_id"])
        if existing:
            existing["reason"] = "Fans also support · shared genre"
            existing["overlap_score"] = max(existing.get("overlap_score", 0), item["overlap_score"])
            continue
        merged[item["owner_id"]] = item

    results = sorted(
        merged.values(),
        key=lambda row: (row.get("overlap_score", 0), row.get("stage_name", "")),
        reverse=True,
    )
    return results[:limit]


def build_targeting_suggestions(artist_user, request, track_id=None):
    """Auto-fill genres, city, and similar-artist targets for the Promote form."""
    profile = None
    try:
        profile = artist_user.artist_profile
    except ArtistProfile.DoesNotExist:
        pass

    genre_terms = set()
    if profile:
        genre_terms |= normalize_genre_terms(profile.genre)
        genre_terms |= normalize_genre_terms(profile.influences)

    track_title = ""
    if track_id:
        from mediahub.models import MusicUpload

        track = MusicUpload.objects.filter(id=track_id, artist=artist_user).first()
        if track:
            track_title = track.title
            genre_terms |= normalize_genre_terms(track.genre)

    similar = similar_artist_suggestions(artist_user, request, limit=MAX_SIMILAR_ARTIST_TARGETS + 3)
    suggested_ids = [row["owner_id"] for row in similar[:MAX_SIMILAR_ARTIST_TARGETS]]

    return {
        "target_genres": " ".join(sorted(genre_terms)),
        "target_location": (profile.city if profile else "") or "",
        "track_title": track_title,
        "similar_artists": similar,
        "suggested_artist_ids": suggested_ids,
        "max_similar_artists": MAX_SIMILAR_ARTIST_TARGETS,
    }


def search_target_artists(artist_user, request, query="", limit=8):
    """Lightweight artist search for the similar-artist picker."""
    query = (query or "").strip()
    if len(query) < 2:
        return []

    limit = min(int(limit or 8), 12)
    filters = Q(stage_name__icontains=query) | Q(genre__icontains=query) | Q(owner__username__icontains=query)
    profiles = (
        ArtistProfile.objects.select_related("owner")
        .exclude(owner=artist_user)
        .filter(on_hiatus=False)
        .filter(filters)
        .order_by("stage_name")[:limit]
    )
    return [
        _serialize_artist_target(profile, request, reason="Search match")
        for profile in profiles
    ]


def resolve_target_artists(campaign):
    ids = campaign.target_artist_id_list()
    if not ids:
        return []

    results = []
    for profile in ArtistProfile.objects.select_related("owner").filter(owner_id__in=ids):
        results.append({
            "owner_id": profile.owner_id,
            "owner_username": profile.owner.username,
            "stage_name": profile.stage_name,
        })

    order = {artist_id: index for index, artist_id in enumerate(ids)}
    results.sort(key=lambda row: order.get(row["owner_id"], 999))
    return results
