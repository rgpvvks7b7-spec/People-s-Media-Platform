from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from config.platform_mode import fan_experience_guard
from artists.business_health import get_artist_business_health
from artists.models import ArtistProfile
from artists.journey import log_fan_journey_event
from artists.models import FanJourneyEvent
from .models import ArtistSignal, TrackSignal
from marketplace.models import Product
from mediahub.models import FanPlaylist, FanPlaylistTrack, MusicUpload
from posts.models import Post
from subscriptions.models import FanSubscription
from spaces.models import SpaceBooking
from artistcalendar.models import ArtistCalendarItem


User = get_user_model()


def split_terms(value):
    return {
        term.strip().lower()
        for chunk in (value or "").replace("/", ",").split(",")
        for term in chunk.split()
        if term.strip()
    }


def text_blob(*values):
    return " ".join(value or "" for value in values).lower()


def add_reason(reasons, label, points, category="general", detail=""):
    if points > 0:
        reasons.append({
            "label": label,
            "points": points,
            "category": category,
            "detail": detail or label,
        })


def add_result(results, profile, request, relaxed=False):
    score, reasons = score_artist(profile, request.user)
    if score <= 0:
        return False

    result = serialize_discovery_artist(profile, request, score, reasons)
    if relaxed:
        result["relaxed_match"] = True
        result["discovery_reasons"] = [
            {"label": "Broader recommendation", "points": 0},
            *result["discovery_reasons"],
        ][:4]
    else:
        result["relaxed_match"] = False

    results.append(result)
    return True


def add_fallback_result(results, profile, request):
    """Surface artists when the taste pool is empty. Skips stay excluded; saved
    artists can reappear as relaxed picks so beta testers are not stuck."""
    if request.user.is_authenticated:
        skip = ArtistSignal.objects.filter(
            fan=request.user,
            artist=profile.owner,
            signal_type=ArtistSignal.SKIP,
        ).exists()
        if skip:
            return False

    own_signal = None
    if request.user.is_authenticated:
        own_signal = ArtistSignal.objects.filter(
            fan=request.user,
            artist=profile.owner,
        ).order_by("-created_at").first()

    score, reasons = score_artist(profile, request.user)
    already_saved = own_signal and own_signal.signal_type == ArtistSignal.SAVE
    if score <= 0:
        score = 12.0
        reasons = [{"label": "Fresh pick for you", "points": 0, "category": "general", "detail": "Fresh pick for you"}]

    result = serialize_discovery_artist(profile, request, score, reasons)
    result["relaxed_match"] = True
    result["already_saved"] = already_saved
    if already_saved:
        result["discovery_reasons"] = [
            {
                "label": "Already saved — rediscover",
                "points": 0,
                "category": "general",
                "detail": "In your saved collection",
            },
            *result["discovery_reasons"],
        ][:4]
    results.append(result)
    return True


def fill_discovery_fallback(results, profiles, request, seen_profile_ids, query, location, profession, limit=6):
    if len(results) >= limit:
        return results

    for profile in profiles:
        if profile.id in seen_profile_ids:
            continue
        if not matches_filter(profile, query, location, profession):
            continue
        if add_fallback_result(results, profile, request):
            seen_profile_ids.add(profile.id)
        if len(results) >= limit:
            break
    return results


def score_artist(profile, request_user):
    artist = profile.owner
    reasons = []
    score = 10

    artist_terms = split_terms(
        f"{profile.genre}, {profile.influences}, {profile.artist_story}, {profile.city}"
    )
    fan_terms = set()
    fan_location = ""

    if request_user.is_authenticated:
        fan_terms = split_terms(request_user.favorite_genres)
        fan_location = (request_user.discovery_location or "").strip().lower()

        positive_signals = ArtistSignal.objects.select_related("artist__artist_profile").filter(
            fan=request_user,
            signal_type__in=[ArtistSignal.SAVE, ArtistSignal.MORE_LIKE_THIS],
        )
        for signal in positive_signals:
            if signal.liked_genre:
                fan_terms.update(split_terms(signal.liked_genre))
            try:
                signaled_profile = signal.artist.artist_profile
            except ArtistProfile.DoesNotExist:
                continue
            fan_terms.update(split_terms(f"{signaled_profile.genre}, {signaled_profile.influences}"))

        own_signal = ArtistSignal.objects.filter(fan=request_user, artist=artist).order_by("-created_at").first()
        if own_signal and own_signal.signal_type == ArtistSignal.SKIP:
            return 0, [{"label": "Skipped by you", "points": 0}]
        if own_signal and own_signal.signal_type == ArtistSignal.SAVE:
            return 0, [{"label": "Already saved by you", "points": 0}]
        if own_signal and own_signal.signal_type == ArtistSignal.MORE_LIKE_THIS:
            score += 18
            add_reason(reasons, "You asked for more like this", 18)

    matched_terms = fan_terms & artist_terms
    genre_points = min(len(matched_terms) * 12, 36)
    score += genre_points
    if matched_terms:
        add_reason(
            reasons,
            f"Matches your taste: {', '.join(sorted(matched_terms)[:3])}",
            genre_points,
            "genre",
            "Artist genre, influences, or story overlaps with your saved genres and discovery signals.",
        )

    if fan_location and fan_location in (profile.city or "").lower():
        score += 14
        add_reason(reasons, f"Near {profile.city}", 14, "location", "Artist city matches your discovery location.")

    connected_artists = []
    if request_user.is_authenticated:
        subscribed_ids = FanSubscription.objects.filter(
            fan=request_user,
            active=True,
        ).values_list("artist_id", flat=True)
        signaled_ids = ArtistSignal.objects.filter(
            fan=request_user,
            signal_type__in=[ArtistSignal.SAVE, ArtistSignal.MORE_LIKE_THIS],
        ).values_list("artist_id", flat=True)
        connected_artists = ArtistProfile.objects.filter(owner_id__in=set(subscribed_ids) | set(signaled_ids))

    similarity_points = 0
    for connected in connected_artists:
        if connected.owner_id == artist.id:
            continue
        connected_terms = split_terms(
            f"{connected.genre}, {connected.influences}, {connected.artist_story}, {connected.city}"
        )
        similarity_points += min(len(artist_terms & connected_terms) * 5, 15)

    similarity_points = min(similarity_points, 25)
    score += similarity_points
    add_reason(
        reasons,
        "Similar to artists you support or saved",
        similarity_points,
        "similarity",
        "This artist shares genre, influence, story, or city terms with artists you support, saved, or asked to see more of.",
    )

    supporters = FanSubscription.objects.filter(artist=artist, active=True).count()
    community_points = min(supporters * 5, 15)
    score += community_points
    add_reason(
        reasons,
        "Early supporter signal",
        community_points,
        "community",
        f"{supporters} active supporters are feeding the community score.",
    )

    business_health = get_artist_business_health(artist, profile)
    ratio_points = min(business_health["supporter_ratio"] / 10, 8)
    if business_health["followers"] < 10:
        ratio_points = min(ratio_points, 3)
    score += ratio_points
    add_reason(
        reasons,
        "Strong supporter conversion",
        ratio_points,
        "business",
        f"{business_health['followers']} followers and {business_health['supporter_ratio_label']}.",
    )

    growth_points = min(business_health["new_subscribers_30d"] * 2, 8)
    score += growth_points
    add_reason(
        reasons,
        "Subscriber growth",
        growth_points,
        "business",
        f"{business_health['new_subscribers_30d']} new subscribers in 30 days.",
    )

    engagement_points = min(business_health["engagement"]["score"] / 4, 5)
    score += engagement_points
    add_reason(
        reasons,
        business_health["engagement"]["badge"],
        engagement_points,
        "engagement",
        "Artist activity and supporter-facing updates add a modest discovery boost.",
    )

    if business_health["is_emerging"]:
        score += 3
        add_reason(
            reasons,
            "Emerging artist",
            3,
            "emerging",
            "New artists get a small separate-lane boost so they are not buried.",
        )

    tracks = MusicUpload.objects.filter(artist=artist).count()
    posts = Post.objects.filter(author=artist).count()
    products = Product.objects.filter(artist=artist, is_active=True).count()
    activity_points = min((tracks * 3) + (posts * 2) + products, 18)
    score += activity_points
    add_reason(
        reasons,
        "Active artist page",
        activity_points,
        "activity",
        f"{tracks} tracks, {posts} posts, and {products} store items contribute to the activity score.",
    )

    uniqueness_source = split_terms(profile.influences)
    uniqueness_points = min(len(uniqueness_source) * 2, 10)
    if len(profile.artist_story or "") > 80:
        uniqueness_points += 4
    uniqueness_points = min(uniqueness_points, 12)
    score += uniqueness_points
    add_reason(reasons, "Distinct artist identity", uniqueness_points, "identity", "Influences and artist story add uniqueness to the ranking.")

    if profile.is_verified:
        score += 5
        add_reason(reasons, "Verified artist", 5, "trust", "Verified artists get a small trust boost.")

    if not profile.genre:
        score -= 8
    if not profile.artist_story:
        score -= 6

    if request_user.is_authenticated and request_user == artist:
        score = -1
        reasons = [{"label": "Your own artist profile", "points": 0}]

    return max(score, 0), reasons


def attach_local_gigs_to_results(results, request):
    location = resolve_scene_location(request)
    if not location or not results:
        return results

    artist_ids = [item["owner_id"] for item in results]
    supported_artist_ids = set()
    if request.user.is_authenticated:
        supported_artist_ids = set(
            FanSubscription.objects.filter(fan=request.user, active=True).values_list("artist_id", flat=True)
        )

    gigs_by_artist = {}
    for booking in confirmed_shows_queryset(location, artist_ids=artist_ids):
        if booking.artist_id in gigs_by_artist:
            continue
        gigs_by_artist[booking.artist_id] = serialize_confirmed_show(booking, request, supported_artist_ids)

    for item in results:
        gig = gigs_by_artist.get(item["owner_id"])
        item["next_local_gig"] = gig
        item["local_gigs"] = [gig] if gig else []

    return results


def get_discovery_excluded_artist_ids(user):
    if not user.is_authenticated:
        return set()

    excluded = set(
        ArtistSignal.objects.filter(
            fan=user,
            signal_type__in=[ArtistSignal.SKIP, ArtistSignal.SAVE],
        ).values_list("artist_id", flat=True)
    )
    excluded.update(
        FanPlaylistTrack.objects.filter(
            playlist__owner=user,
        ).values_list("track__artist_id", flat=True).distinct()
    )
    return excluded


def get_discovery_excluded_track_ids(user):
    if not user.is_authenticated:
        return set()

    excluded = set(
        TrackSignal.objects.filter(
            fan=user,
            signal_type__in=[TrackSignal.SKIP, TrackSignal.SAVE],
        ).values_list("track_id", flat=True)
    )
    excluded.update(
        FanPlaylistTrack.objects.filter(
            playlist__owner=user,
        ).values_list("track_id", flat=True).distinct()
    )
    return excluded


def track_matches_filter(track, query, profession=""):
    try:
        profile = track.artist.artist_profile
    except ArtistProfile.DoesNotExist:
        return False

    if profession and profession not in profile.profession_list() and profession != track.profession:
        return False

    if query:
        searchable = text_blob(
            track.title,
            track.genre,
            track.artist.username,
            profile.stage_name,
            profile.city,
        )
        if query not in searchable:
            return False

    return True


def score_track(track, request_user):
    try:
        profile = track.artist.artist_profile
    except ArtistProfile.DoesNotExist:
        return 0, [{"label": "Missing artist profile", "points": 0}]

    artist_score, artist_reasons = score_artist(profile, request_user)
    if artist_score <= 0:
        return 0, artist_reasons

    score = max(artist_score * 0.72, 0)
    reasons = list(artist_reasons[:3])

    track_terms = split_terms(track.genre)
    if track_terms:
        add_reason(
            reasons,
            f"Track genre: {track.genre or 'Unknown'}",
            6,
            "genre",
            "Song genre contributes to the track discovery score.",
        )
        score += 6

    if track.bpm:
        add_reason(
            reasons,
            f"{track.bpm} BPM",
            3,
            "activity",
            "Tempo adds a small activity signal for track discovery.",
        )
        score += 3

    if request_user.is_authenticated:
        own_signal = TrackSignal.objects.filter(
            fan=request_user,
            track=track,
        ).order_by("-created_at").first()
        if own_signal and own_signal.signal_type == TrackSignal.SKIP:
            return 0, [{"label": "Skipped by you", "points": 0}]
        if own_signal and own_signal.signal_type == TrackSignal.SAVE:
            return 0, [{"label": "Already saved by you", "points": 0}]

    return max(score, 0), reasons


def serialize_discovery_track(track, request, score, reasons, relaxed=False):
    from mediahub.views import serialize_track

    payload = serialize_track(track, request)
    if not payload.get("audio_file") and not payload.get("preview_audio_file"):
        return None

    profile = track.artist.artist_profile
    viewer_signal = None
    if request.user.is_authenticated:
        signal = TrackSignal.objects.filter(
            fan=request.user,
            track=track,
        ).order_by("-created_at").first()
        viewer_signal = signal.signal_type if signal else None

    result = {
        **payload,
        "discovery_score": round(score, 2),
        "discovery_reasons": reasons[:4],
        "relaxed_match": relaxed,
        "promoted": False,
        "promotion": None,
        "viewer_signal": viewer_signal,
        "artist": {
            "owner_id": track.artist_id,
            "owner_username": track.artist.username,
            "stage_name": profile.stage_name,
            "genre": profile.genre,
            "city": profile.city,
            "hero_image": request.build_absolute_uri(profile.hero_image.url) if profile.hero_image else None,
            "is_verified": profile.is_verified,
        },
    }
    return result


def add_track_result(results, track, request, relaxed=False):
    score, reasons = score_track(track, request.user)
    if score <= 0:
        return False

    result = serialize_discovery_track(track, request, score, reasons, relaxed=relaxed)
    if not result:
        return False

    if relaxed:
        result["discovery_reasons"] = [
            {"label": "Broader recommendation", "points": 0, "category": "general", "detail": "Broader recommendation"},
            *result["discovery_reasons"],
        ][:4]

    results.append(result)
    return True


def discovery_preview_track(artist, request):
    from mediahub.views import serialize_track

    track = MusicUpload.objects.filter(artist=artist).order_by("-created_at").first()
    if not track:
        return None

    payload = serialize_track(track, request)
    if not payload.get("audio_file") and not payload.get("preview_audio_file"):
        return None

    return {
        "id": payload["id"],
        "title": payload["title"],
        "genre": payload["genre"],
        "bpm": payload["bpm"],
        "cover_art": payload["cover_art"],
        "audio_file": payload["audio_file"],
        "preview_audio_file": payload["preview_audio_file"],
        "preview_seconds": payload["preview_seconds"],
        "can_preview": payload.get("can_preview"),
    }


def serialize_discovery_artist(profile, request, score, reasons):
    artist = profile.owner
    supporters = FanSubscription.objects.filter(artist=artist, active=True).count()
    tracks = MusicUpload.objects.filter(artist=artist).count()
    posts = Post.objects.filter(author=artist).count()
    products = Product.objects.filter(artist=artist, is_active=True).count()
    viewer_signal = None
    profession_profiles = {
        item.profession: item
        for item in profile.profession_profiles.all()
    }

    if request.user.is_authenticated:
        signal = ArtistSignal.objects.filter(
            fan=request.user,
            artist=artist,
        ).order_by("-created_at").first()
        viewer_signal = signal.signal_type if signal else None
    business_health = get_artist_business_health(artist, profile)

    return {
        "id": profile.id,
        "stage_name": profile.stage_name,
        "genre": profile.genre,
        "city": profile.city,
        "artist_story": profile.artist_story,
        "influences": profile.influences,
        "is_verified": profile.is_verified,
        "on_hiatus": profile.on_hiatus,
        "business_health": business_health,
        "professions": [
            {"key": profession, "label": ArtistProfile.profession_label(profession)}
            for profession in profile.profession_list()
        ],
        "profession_keys": profile.profession_list(),
        "profession_profiles": {
            profession: {
                "profession": profession,
                "label": ArtistProfile.profession_label(profession),
                "display_title": profession_profiles[profession].display_title if profession in profession_profiles else "",
                "tagline": profession_profiles[profession].tagline if profession in profession_profiles else "",
                "bio": profession_profiles[profession].bio if profession in profession_profiles else "",
                "style": profession_profiles[profession].style if profession in profession_profiles else "",
                "cover_image": request.build_absolute_uri(profession_profiles[profession].cover_image.url)
                if profession in profession_profiles and profession_profiles[profession].cover_image else None,
            }
            for profession in profile.profession_list()
        },
        "owner_id": artist.id,
        "owner_username": artist.username,
        "hero_image": request.build_absolute_uri(profile.hero_image.url) if profile.hero_image else None,
        "show_music": profile.show_music,
        "show_posts": profile.show_posts,
        "show_store": profile.show_store,
        "show_lives": profile.show_lives,
        "show_about": profile.show_about,
        "discovery_score": round(score, 2),
        "discovery_reasons": reasons[:4],
        "promoted": False,
        "promotion": None,
        "signals": {
            "supporters": supporters,
            "followers": business_health["followers"],
            "supporter_ratio": business_health["supporter_ratio"],
            "engagement_badge": business_health["engagement"]["badge"],
            "is_emerging": business_health["is_emerging"],
            "tracks": tracks,
            "posts": posts,
            "products": products,
        },
        "viewer_signal": viewer_signal,
        "preview_track": discovery_preview_track(artist, request),
    }


def matches_filter(profile, query, location, profession=""):
    if profession:
        if profession not in profile.profession_list():
            return False

    if location:
        if location not in (profile.city or "").lower():
            return False

    if query:
        searchable = text_blob(
            profile.stage_name,
            profile.owner.username,
            profile.genre,
            profile.artist_story,
            profile.influences,
            profile.city,
        )
        if query not in searchable:
            return False

    return True

def _promotion_label(campaign, genre=""):
    location = (campaign.target_location or "").strip()
    genre = (genre or "").strip()
    if location:
        return f"Featured {location} artist"
    if genre:
        return f"Featured {genre.split(',')[0].strip().title()} release"
    return "Promoted release"


def _interleave_promoted(results, promoted, every=4):
    """Reserve ~1 in `every` slots for promoted items so organic discovery is
    never displaced. Promoted items are spaced through the list."""
    if not promoted:
        return results
    merged = []
    promo_iter = iter(promoted)
    next_promo = next(promo_iter, None)
    position = 0
    organic_iter = iter(results)
    while True:
        if next_promo is not None and position % every == 1:
            merged.append(next_promo)
            next_promo = next(promo_iter, None)
            position += 1
            continue
        organic = next(organic_iter, None)
        if organic is None:
            break
        merged.append(organic)
        position += 1
    # Append any promoted items that didn't get an interleave slot.
    while next_promo is not None:
        merged.append(next_promo)
        next_promo = next(promo_iter, None)
    return merged


def inject_promoted_tracks(results, request, excluded_track_ids, excluded_artist_ids):
    try:
        from promotions.models import Campaign
        from promotions.services import campaigns_for_fan, fan_discovery_prefs, record_impression
    except Exception:
        return results

    user = request.user
    prefs = fan_discovery_prefs(user)
    campaigns = campaigns_for_fan(Campaign.TRACK, user, prefs=prefs)
    if not campaigns:
        return results

    max_promoted = 1 if prefs.get("fewer_promoted") else 3
    interleave_every = 8 if prefs.get("fewer_promoted") else 4

    results_by_id = {item["id"]: item for item in results}
    existing_ids = set(results_by_id)
    promoted = []
    for campaign in campaigns:
        track = (
            MusicUpload.objects
            .select_related("artist", "artist__artist_profile", "library_cover")
            .filter(id=campaign.target_id)
            .first()
        )
        if not track:
            continue
        # If the promoted track is already organically listed, upgrade it in
        # place to a promoted slot rather than duplicating it.
        if track.id in results_by_id:
            existing = results_by_id[track.id]
            if not existing.get("promoted"):
                existing["promoted"] = True
                existing["promotion"] = {
                    "campaign_id": campaign.id,
                    "label": _promotion_label(campaign, track.genre),
                }
                record_impression(campaign, user)
            continue
        if user.is_authenticated and (
            track.id in excluded_track_ids or track.artist_id in excluded_artist_ids
        ):
            continue
        score, reasons = score_track(track, user)
        payload = serialize_discovery_track(
            track, request, score if score > 0 else 1.0,
            reasons or [{"label": "Promoted", "points": 0}],
        )
        if not payload:
            continue
        payload["promoted"] = True
        payload["promotion"] = {"campaign_id": campaign.id, "label": _promotion_label(campaign, track.genre)}
        promoted.append(payload)
        existing_ids.add(track.id)
        record_impression(campaign, user)
        if len(promoted) >= max_promoted:
            break

    return _interleave_promoted(results, promoted, every=interleave_every)


def inject_promoted_artists(results, request, excluded_artist_ids):
    try:
        from promotions.models import Campaign
        from promotions.services import campaigns_for_fan, fan_discovery_prefs, record_impression
    except Exception:
        return results

    user = request.user
    prefs = fan_discovery_prefs(user)
    campaigns = campaigns_for_fan(Campaign.PROFILE, user, prefs=prefs)
    if not campaigns:
        return results

    max_promoted = 1 if prefs.get("fewer_promoted") else 3
    interleave_every = 8 if prefs.get("fewer_promoted") else 4

    results_by_owner = {item["owner_id"]: item for item in results}
    existing_owner_ids = set(results_by_owner)
    promoted = []
    for campaign in campaigns:
        if campaign.target_id in results_by_owner:
            existing = results_by_owner[campaign.target_id]
            if not existing.get("promoted"):
                profile_genre = existing.get("genre", "")
                existing["promoted"] = True
                existing["promotion"] = {
                    "campaign_id": campaign.id,
                    "label": _promotion_label(campaign, profile_genre),
                }
                record_impression(campaign, user)
            continue
        if user.is_authenticated and campaign.target_id in excluded_artist_ids:
            continue
        try:
            profile = ArtistProfile.objects.select_related("owner").get(owner_id=campaign.target_id)
        except ArtistProfile.DoesNotExist:
            continue
        score, reasons = score_artist(profile, user)
        payload = serialize_discovery_artist(
            profile, request, score if score > 0 else 1.0,
            reasons or [{"label": "Promoted", "points": 0}],
        )
        payload["relaxed_match"] = False
        payload["promoted"] = True
        payload["promotion"] = {"campaign_id": campaign.id, "label": _promotion_label(campaign, profile.genre)}
        promoted.append(payload)
        existing_owner_ids.add(campaign.target_id)
        record_impression(campaign, user)
        if len(promoted) >= max_promoted:
            break

    return _interleave_promoted(results, promoted, every=interleave_every)


@api_view(['GET'])
def index(request):
    return Response({'app': 'discovery', 'status': 'ready'})


@api_view(["GET"])
def artist_recommendations(request):
    blocked = fan_experience_guard(request)
    if blocked:
        return blocked

    query = (request.query_params.get("q") or "").strip().lower()
    location = (request.query_params.get("location") or "").strip().lower()
    profession = (request.query_params.get("profession") or "").strip()
    if profession and profession not in ArtistProfile.valid_profession_keys():
        return Response({"error": "Invalid profession"}, status=status.HTTP_400_BAD_REQUEST)
    backfill = (request.query_params.get("backfill") or "").lower() in {"1", "true", "yes"}

    profiles = ArtistProfile.objects.select_related("owner").order_by("-created_at")
    results = []
    seen_profile_ids = set()
    skipped_count = 0
    excluded_artist_ids = get_discovery_excluded_artist_ids(request.user)

    for profile in profiles:
        if not matches_filter(profile, query, location, profession):
            continue

        if request.user.is_authenticated and profile.owner_id in excluded_artist_ids:
            if ArtistSignal.objects.filter(
                fan=request.user,
                artist=profile.owner,
                signal_type=ArtistSignal.SKIP,
            ).exists():
                skipped_count += 1
            continue

        if add_result(results, profile, request):
            seen_profile_ids.add(profile.id)

    if backfill and len(results) < 6:
        for profile in profiles:
            if profile.id in seen_profile_ids:
                continue
            if request.user.is_authenticated and profile.owner_id in excluded_artist_ids:
                continue
            matched = matches_filter(profile, query, location, profession)
            if add_result(results, profile, request, relaxed=not matched):
                seen_profile_ids.add(profile.id)
            if len(results) >= 6:
                break

    if request.user.is_authenticated and len(results) == 0:
        fill_discovery_fallback(
            results,
            profiles,
            request,
            seen_profile_ids,
            query,
            location,
            profession,
            limit=6,
        )

    results.sort(
        key=lambda artist: (
            not artist.get("already_saved", False),
            not artist["relaxed_match"],
            artist["discovery_score"],
            artist["signals"]["supporters"],
            artist["signals"]["tracks"] + artist["signals"]["posts"],
            artist["id"],
        ),
        reverse=True,
    )
    if request.user.is_authenticated and getattr(request.user, "discovery_prefer_emerging", False):
        results.sort(
            key=lambda artist: (
                not artist["business_health"]["is_emerging"],
                not artist["relaxed_match"],
                -artist["discovery_score"],
                artist["id"],
            ),
        )
    emerging_results = [artist for artist in results if artist["business_health"]["is_emerging"]]
    results = inject_promoted_artists(results, request, excluded_artist_ids)
    results = attach_local_gigs_to_results(results, request)

    return Response({
        "results": results,
        "emerging": emerging_results[:6],
        "count": len(results),
        "personalized": request.user.is_authenticated,
        "skipped_count": skipped_count,
        "exhausted": request.user.is_authenticated and len(results) == 0,
    })


@api_view(["GET"])
def track_recommendations(request):
    blocked = fan_experience_guard(request)
    if blocked:
        return blocked

    query = (request.query_params.get("q") or "").strip().lower()
    location = (request.query_params.get("location") or "").strip().lower()
    profession = (request.query_params.get("profession") or "").strip()
    if profession and profession not in ArtistProfile.valid_profession_keys():
        return Response({"error": "Invalid profession"}, status=status.HTTP_400_BAD_REQUEST)
    backfill = (request.query_params.get("backfill") or "").lower() in {"1", "true", "yes"}

    tracks = MusicUpload.objects.select_related("artist", "artist__artist_profile", "library_cover").order_by("-created_at")
    results = []
    seen_track_ids = set()
    skipped_count = 0
    excluded_track_ids = get_discovery_excluded_track_ids(request.user)
    excluded_artist_ids = get_discovery_excluded_artist_ids(request.user)

    for track in tracks:
        if not track_matches_filter(track, query, profession):
            continue

        if location:
            try:
                if location not in (track.artist.artist_profile.city or "").lower():
                    continue
            except ArtistProfile.DoesNotExist:
                continue

        if request.user.is_authenticated:
            if track.id in excluded_track_ids or track.artist_id in excluded_artist_ids:
                if TrackSignal.objects.filter(
                    fan=request.user,
                    track=track,
                    signal_type=TrackSignal.SKIP,
                ).exists():
                    skipped_count += 1
                continue

        if add_track_result(results, track, request):
            seen_track_ids.add(track.id)

    if backfill and len(results) < 6:
        for track in tracks:
            if track.id in seen_track_ids:
                continue
            if request.user.is_authenticated and (
                track.id in excluded_track_ids or track.artist_id in excluded_artist_ids
            ):
                continue
            matched = track_matches_filter(track, query, profession)
            if add_track_result(results, track, request, relaxed=not matched):
                seen_track_ids.add(track.id)
            if len(results) >= 6:
                break

    results.sort(
        key=lambda item: (
            not item["relaxed_match"],
            item["discovery_score"],
            item["id"],
        ),
        reverse=True,
    )

    results = inject_promoted_tracks(results, request, excluded_track_ids, excluded_artist_ids)

    return Response({
        "results": results,
        "count": len(results),
        "personalized": request.user.is_authenticated,
        "skipped_count": skipped_count,
        "exhausted": request.user.is_authenticated and len(results) == 0,
    })


@api_view(["GET"])
def saved_artists(request):
    blocked = fan_experience_guard(request)
    if blocked:
        return blocked

    if not request.user.is_authenticated:
        return Response({"results": [], "count": 0, "authenticated": False})

    signals = ArtistSignal.objects.select_related("artist__artist_profile").filter(
        fan=request.user,
        signal_type=ArtistSignal.SAVE,
    ).order_by("-created_at")
    results = []

    for signal in signals:
        try:
            profile = signal.artist.artist_profile
        except ArtistProfile.DoesNotExist:
            continue

        score, reasons = score_artist(profile, request.user)
        results.append(serialize_discovery_artist(profile, request, score, reasons))

    results = attach_local_gigs_to_results(results, request)

    return Response({
        "results": results,
        "count": len(results),
        "authenticated": True,
    })


@api_view(["POST"])
def record_artist_signal(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    artist_id = request.data.get("artist_id")
    signal_type = request.data.get("signal_type")

    if signal_type not in {ArtistSignal.SAVE, ArtistSignal.SKIP, ArtistSignal.MORE_LIKE_THIS}:
        return Response({"error": "Invalid signal type"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        artist = User.objects.get(id=artist_id)
        profile = artist.artist_profile
    except User.DoesNotExist:
        return Response({"error": "Artist not found"}, status=status.HTTP_404_NOT_FOUND)
    except ArtistProfile.DoesNotExist:
        return Response({"error": "Artist profile not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.user == artist:
        return Response({"error": "You cannot signal your own artist profile"}, status=status.HTTP_400_BAD_REQUEST)

    if signal_type == ArtistSignal.SKIP:
        ArtistSignal.objects.filter(fan=request.user, artist=artist).exclude(signal_type=ArtistSignal.SKIP).delete()
    else:
        ArtistSignal.objects.filter(fan=request.user, artist=artist, signal_type=ArtistSignal.SKIP).delete()

    signal, created = ArtistSignal.objects.update_or_create(
        fan=request.user,
        artist=artist,
        signal_type=signal_type,
        defaults={
            "liked_genre": profile.genre,
            "weight": {
                ArtistSignal.SAVE: 1.4,
                ArtistSignal.MORE_LIKE_THIS: 1.2,
                ArtistSignal.SKIP: -1.0,
            }[signal_type],
            "reason": {
                ArtistSignal.SAVE: "Saved artist from discovery",
                ArtistSignal.MORE_LIKE_THIS: "Asked for similar artists",
                ArtistSignal.SKIP: "Skipped artist from discovery",
            }[signal_type],
        },
    )
    if signal_type == ArtistSignal.SAVE:
        from artists.models import ArtistFollow

        ArtistFollow.objects.get_or_create(fan=request.user, artist=artist)
        referral_source = request.data.get("referral_source") or request.query_params.get("ref") or ""
        log_fan_journey_event(
            FanJourneyEvent.FOLLOW,
            artist,
            fan=request.user,
            metadata={"referral_source": referral_source, "source": "discovery_save"},
        )
        log_fan_journey_event(
            FanJourneyEvent.CONTENT_ENGAGEMENT,
            artist,
            fan=request.user,
            metadata={
                "engagement_type": "save",
                "source": "discovery",
                "referral_source": referral_source,
            },
        )
        try:
            from promotions.models import Campaign
            from promotions.services import charge_engagement

            charge_engagement(Campaign.PROFILE, artist.id, request.user, "follow")
        except Exception:
            pass

    return Response({
        "created": created,
        "signal": {
            "id": signal.id,
            "artist_id": artist.id,
            "artist": artist.username,
            "signal_type": signal.signal_type,
            "liked_genre": signal.liked_genre,
        },
        "message": "Discovery signal saved.",
    })


@api_view(["POST"])
def record_track_signal(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    track_id = request.data.get("track_id")
    signal_type = request.data.get("signal_type")

    if signal_type not in {TrackSignal.SAVE, TrackSignal.SKIP}:
        return Response({"error": "Invalid signal type"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        track = MusicUpload.objects.select_related("artist").get(id=track_id)
    except MusicUpload.DoesNotExist:
        return Response({"error": "Track not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.user == track.artist:
        return Response({"error": "You cannot signal your own track"}, status=status.HTTP_400_BAD_REQUEST)

    if signal_type == TrackSignal.SKIP:
        TrackSignal.objects.filter(fan=request.user, track=track).exclude(signal_type=TrackSignal.SKIP).delete()
    else:
        TrackSignal.objects.filter(fan=request.user, track=track, signal_type=TrackSignal.SKIP).delete()

    signal, created = TrackSignal.objects.update_or_create(
        fan=request.user,
        track=track,
        signal_type=signal_type,
        defaults={
            "liked_genre": track.genre,
            "weight": 1.2 if signal_type == TrackSignal.SAVE else -1.0,
            "reason": {
                TrackSignal.SAVE: "Saved track from discovery",
                TrackSignal.SKIP: "Skipped track from discovery",
            }[signal_type],
        },
    )

    playlist_payload = None
    if signal_type == TrackSignal.SAVE:
        playlist, _ = FanPlaylist.objects.get_or_create(
            owner=request.user,
            title="Discovery Saves",
            defaults={"description": "Tracks saved while swiping discovery."},
        )
        FanPlaylistTrack.objects.get_or_create(playlist=playlist, track=track)
        playlist_payload = {"id": playlist.id, "title": playlist.title}
        try:
            from promotions.models import Campaign
            from promotions.services import charge_engagement

            charge_engagement(Campaign.TRACK, track.id, request.user, "save")
        except Exception:
            pass

    return Response({
        "created": created,
        "signal": {
            "id": signal.id,
            "track_id": track.id,
            "signal_type": signal.signal_type,
            "liked_genre": signal.liked_genre,
        },
        "playlist": playlist_payload,
        "message": "Track discovery signal saved.",
    })


@api_view(["POST"])
def undo_track_skip(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    track_id = request.data.get("track_id")
    deleted_count, _ = TrackSignal.objects.filter(
        fan=request.user,
        track_id=track_id,
        signal_type=TrackSignal.SKIP,
    ).delete()

    return Response({
        "message": "Track skip undone.",
        "deleted_count": deleted_count,
    })


@api_view(["POST"])
def reset_skipped_artists(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    deleted_count, _ = ArtistSignal.objects.filter(
        fan=request.user,
        signal_type=ArtistSignal.SKIP,
    ).delete()

    return Response({
        "message": "Skipped artists reset.",
        "deleted_count": deleted_count,
    })


@api_view(["POST"])
def undo_skip_artist(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    artist_id = request.data.get("artist_id")
    deleted_count, _ = ArtistSignal.objects.filter(
        fan=request.user,
        artist_id=artist_id,
        signal_type=ArtistSignal.SKIP,
    ).delete()

    return Response({
        "message": "Skip undone.",
        "deleted_count": deleted_count,
    })


@api_view(["POST"])
def remove_saved_artist(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    artist_id = request.data.get("artist_id")
    deleted_count, _ = ArtistSignal.objects.filter(
        fan=request.user,
        artist_id=artist_id,
        signal_type=ArtistSignal.SAVE,
    ).delete()

    return Response({
        "message": "Artist removed from saved.",
        "deleted_count": deleted_count,
    })


@api_view(["POST"])
def undo_artist_signal(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    artist_id = request.data.get("artist_id")
    signal_type = request.data.get("signal_type")

    if signal_type not in {ArtistSignal.SAVE, ArtistSignal.SKIP, ArtistSignal.MORE_LIKE_THIS}:
        return Response({"error": "Invalid signal type"}, status=status.HTTP_400_BAD_REQUEST)

    deleted_count, _ = ArtistSignal.objects.filter(
        fan=request.user,
        artist_id=artist_id,
        signal_type=signal_type,
    ).delete()

    return Response({
        "message": "Discovery action undone.",
        "deleted_count": deleted_count,
    })


SHOW_HORIZON_DAYS = 45


def resolve_scene_location(request):
    location = (request.query_params.get("location") or "").strip()
    if request.user.is_authenticated and not location:
        location = (request.user.discovery_location or "").strip()
    return location


def confirmed_shows_queryset(location="", artist_ids=None):
    now = timezone.now()
    horizon = now + timezone.timedelta(days=SHOW_HORIZON_DAYS)
    queryset = (
        SpaceBooking.objects
        .select_related(
            "artist",
            "artist__artist_profile",
            "listing",
            "listing__host",
            "listing__host__host_profile",
            "ticket_product",
        )
        .filter(
            status=SpaceBooking.CONFIRMED,
            starts_at__gte=now,
            starts_at__lte=horizon,
        )
    )
    if location:
        queryset = queryset.filter(listing__city__icontains=location)
    if artist_ids is not None:
        queryset = queryset.filter(artist_id__in=artist_ids)
    return queryset.order_by("starts_at")


def serialize_confirmed_show(booking, request, supported_artist_ids=None):
    from spaces.services import ensure_booking_ticket_product

    if booking.status == SpaceBooking.CONFIRMED and not booking.ticket_product_id:
        ensure_booking_ticket_product(booking)
        booking.refresh_from_db()

    profile = getattr(booking.artist, "artist_profile", None)
    host_profile = getattr(booking.listing.host, "host_profile", None)
    calendar_item = ArtistCalendarItem.objects.filter(space_booking=booking).first()
    business_health = get_artist_business_health(booking.artist, profile) if profile else {
        "supporter_ratio": 0,
        "engagement": {"badge": "New"},
    }
    supported_artist_ids = supported_artist_ids or set()
    ticket = None
    ticket_product = getattr(booking, "ticket_product", None)
    if ticket_product and ticket_product.is_active:
        ticket = {
            "id": ticket_product.id,
            "title": ticket_product.title,
            "price": str(ticket_product.price),
            "description": ticket_product.description,
        }
    elif booking.ticket_product_id:
        try:
            product = Product.objects.get(id=booking.ticket_product_id, is_active=True)
            ticket = {
                "id": product.id,
                "title": product.title,
                "price": str(product.price),
                "description": product.description,
            }
        except Product.DoesNotExist:
            pass

    from spaces.ticket_inventory import ticket_availability_for_booking

    availability = ticket_availability_for_booking(booking)
    if ticket:
        ticket["sold_out"] = availability["sold_out"]
        ticket["remaining"] = availability["remaining"]

    payload = {
        "booking_id": booking.id,
        "starts_at": booking.starts_at,
        "ends_at": booking.ends_at,
        "venue_name": booking.listing.name,
        "venue_city": booking.listing.city,
        "venue_address": booking.listing.address,
        "listing_id": booking.listing_id,
        "host_business_name": host_profile.business_name if host_profile else booking.listing.host.display_name,
        "bar_open": booking.listing.bar_open,
        "kitchen_open": booking.listing.kitchen_open,
        "drink_minimum": booking.listing.drink_minimum,
        "last_call": booking.listing.last_call,
        "artist_id": booking.artist_id,
        "artist_username": booking.artist.username,
        "stage_name": profile.stage_name if profile else booking.artist.username,
        "genre": profile.genre if profile else "",
        "supporter_ratio": business_health["supporter_ratio"],
        "engagement_badge": business_health["engagement"]["badge"],
        "ticket_product_id": booking.ticket_product_id,
        "ticket": ticket,
        "calendar_item_id": calendar_item.id if calendar_item else None,
        "is_supported": booking.artist_id in supported_artist_ids,
        "ticket_availability": availability,
    }
    if request.user.is_authenticated and booking.ticket_product_id:
        from spaces.ticket_admission import enrich_show_fan_check_in

        enrich_show_fan_check_in(payload, booking, request.user)
    return payload


@api_view(["GET"])
def playing_near_you(request):
    blocked = fan_experience_guard(request)
    if blocked:
        return blocked

    location = resolve_scene_location(request)
    if not location:
        return Response({"results": [], "count": 0, "location": ""})

    supported_artist_ids = set()
    if request.user.is_authenticated:
        supported_artist_ids = set(
            FanSubscription.objects.filter(fan=request.user, active=True).values_list("artist_id", flat=True)
        )

    results = []
    for booking in confirmed_shows_queryset(location)[:50]:
        profile = getattr(booking.artist, "artist_profile", None)
        if not profile:
            continue
        results.append(serialize_confirmed_show(booking, request, supported_artist_ids))

    return Response({"results": results, "count": len(results), "location": location})


@api_view(["GET"])
def my_scene(request):
    blocked = fan_experience_guard(request)
    if blocked:
        return blocked

    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    location = resolve_scene_location(request)
    supported_artist_ids = set(
        FanSubscription.objects.filter(fan=request.user, active=True).values_list("artist_id", flat=True)
    )

    if not location:
        return Response({
            "location": "",
            "all_shows": [],
            "supported_shows": [],
            "counts": {"all": 0, "supported": 0},
            "needs_location": True,
        })

    all_shows = []
    supported_shows = []
    for booking in confirmed_shows_queryset(location)[:50]:
        profile = getattr(booking.artist, "artist_profile", None)
        if not profile:
            continue
        item = serialize_confirmed_show(booking, request, supported_artist_ids)
        all_shows.append(item)
        if item["is_supported"]:
            supported_shows.append(item)

    return Response({
        "location": location,
        "all_shows": all_shows,
        "supported_shows": supported_shows,
        "counts": {"all": len(all_shows), "supported": len(supported_shows)},
        "needs_location": False,
    })


@api_view(["GET"])
def show_detail(request, booking_id):
    try:
        booking = (
            SpaceBooking.objects
            .select_related(
                "artist",
                "artist__artist_profile",
                "listing",
                "listing__host",
                "listing__host__host_profile",
                "ticket_product",
            )
            .get(
                id=booking_id,
                status__in=[SpaceBooking.CONFIRMED, SpaceBooking.COMPLETED],
            )
        )
    except SpaceBooking.DoesNotExist:
        return Response({"error": "Show not found"}, status=status.HTTP_404_NOT_FOUND)

    profile = getattr(booking.artist, "artist_profile", None)
    if not profile:
        return Response({"error": "Show not found"}, status=status.HTTP_404_NOT_FOUND)

    supported_artist_ids = set()
    if request.user.is_authenticated:
        if FanSubscription.objects.filter(
            fan=request.user,
            artist=booking.artist,
            active=True,
        ).exists():
            supported_artist_ids.add(booking.artist_id)

    show = serialize_confirmed_show(booking, request, supported_artist_ids)
    show["pitch"] = booking.pitch
    show["status"] = booking.status
    show["has_ended"] = booking.status == SpaceBooking.COMPLETED or (
        booking.ends_at is not None and booking.ends_at < timezone.now()
    )
    return Response({"show": show})


@api_view(["GET"])
def global_search(request):
    blocked = fan_experience_guard(request)
    if blocked:
        return blocked

    query = (request.query_params.get("q") or "").strip()
    if len(query) < 2:
        return Response({"artists": [], "tracks": [], "posts": []})

    q_lower = query.lower()
    artists = []
    for profile in ArtistProfile.objects.select_related("owner").filter(on_hiatus=False)[:200]:
        blob = text_blob(profile.stage_name, profile.genre, profile.city, profile.owner.username)
        if q_lower in blob:
            artists.append({
                "id": profile.owner_id,
                "username": profile.owner.username,
                "stage_name": profile.stage_name,
                "city": profile.city,
                "genre": profile.genre,
                "is_featured": profile.is_featured,
            })
    artists = artists[:12]

    tracks = []
    for track in MusicUpload.objects.select_related("artist").filter(title__icontains=query)[:12]:
        tracks.append({
            "id": track.id,
            "title": track.title,
            "artist_id": track.artist_id,
            "artist_username": track.artist.username,
            "profession": track.profession,
        })

    posts = []
    for post in Post.objects.select_related("author").filter(is_hidden=False).filter(
        models.Q(title__icontains=query) | models.Q(body__icontains=query)
    )[:12]:
        posts.append({
            "id": post.id,
            "title": post.title,
            "body": post.body[:160],
            "author_username": post.author.username,
            "post_type": post.post_type,
        })

    return Response({"artists": artists, "tracks": tracks, "posts": posts})


@api_view(["GET"])
def featured_artists(request):
    profiles = (
        ArtistProfile.objects.select_related("owner")
        .filter(is_featured=True, on_hiatus=False)
        .order_by("-created_at")[:12]
    )
    results = []
    for profile in profiles:
        results.append({
            "id": profile.owner_id,
            "username": profile.owner.username,
            "stage_name": profile.stage_name,
            "city": profile.city,
            "genre": profile.genre,
        })
    return Response({"results": results, "count": len(results)})
