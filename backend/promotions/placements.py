from mediahub.models import MusicUpload

from .models import Campaign
from .services import campaigns_for_fan, fan_discovery_prefs, record_impression


def promotion_label(campaign, genre=""):
    if campaign.target_location:
        return f"Featured {campaign.target_location} artist"
    terms = campaign.target_genre_terms()
    if terms:
        return f"Featured {' '.join(sorted(terms)[:2]).title()} release"
    if genre:
        return f"Featured {genre.split(',')[0].strip().title()} release"
    return "Promoted release"


def _track_campaign_payload(campaign, request, user):
    from discovery.views import score_track, serialize_discovery_track

    track = (
        MusicUpload.objects
        .select_related("artist", "artist__artist_profile", "library_cover")
        .filter(id=campaign.target_id)
        .first()
    )
    if not track:
        return None

    score, reasons = score_track(track, user)
    payload = serialize_discovery_track(
        track,
        request,
        score if score > 0 else 1.0,
        reasons or [{"label": "Promoted", "points": 0}],
    )
    if not payload:
        return None

    payload["promoted"] = True
    payload["promotion"] = {
        "campaign_id": campaign.id,
        "label": promotion_label(campaign, track.genre),
        "surface": "placement",
    }
    record_impression(campaign, user)
    return payload


def _profile_campaign_payload(campaign, request, user):
    from artists.models import ArtistProfile
    from discovery.views import score_artist, serialize_discovery_artist

    try:
        profile = ArtistProfile.objects.select_related("owner").get(owner_id=campaign.target_id)
    except ArtistProfile.DoesNotExist:
        return None

    score, reasons = score_artist(profile, user)
    payload = serialize_discovery_artist(
        profile,
        request,
        score if score > 0 else 1.0,
        reasons or [{"label": "Promoted", "points": 0}],
    )
    payload["promoted"] = True
    payload["promotion"] = {
        "campaign_id": campaign.id,
        "label": promotion_label(campaign, profile.genre),
        "surface": "placement",
    }
    record_impression(campaign, user)
    return payload


def placements_for_surface(request, surface, *, artist_id=None, limit=2):
    user = request.user
    prefs = fan_discovery_prefs(user)
    limit = max(1, min(int(limit or 2), 4))

    track_campaigns = campaigns_for_fan(Campaign.TRACK, user, prefs=prefs)
    profile_campaigns = campaigns_for_fan(Campaign.PROFILE, user, prefs=prefs)

    if artist_id:
        track_campaigns = [c for c in track_campaigns if c.artist_id != artist_id]
        profile_campaigns = [c for c in profile_campaigns if c.target_id != artist_id]

    if prefs.get("fewer_promoted"):
        limit = 1

    results = []
    for campaign in track_campaigns:
        payload = _track_campaign_payload(campaign, request, user)
        if payload:
            results.append(payload)
        if len(results) >= limit:
            break

    if surface == "artist_page" and len(results) < limit:
        for campaign in profile_campaigns:
            payload = _profile_campaign_payload(campaign, request, user)
            if payload:
                results.append(payload)
            if len(results) >= limit:
                break

    return results
