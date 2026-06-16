from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from artists.models import ArtistProfile
from .models import ArtistSignal
from marketplace.models import Product
from mediahub.models import MusicUpload
from posts.models import Post
from subscriptions.models import FanSubscription


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
            score += 24
            add_reason(reasons, "Saved by you", 24)
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


def serialize_discovery_artist(profile, request, score, reasons):
    artist = profile.owner
    supporters = FanSubscription.objects.filter(artist=artist, active=True).count()
    tracks = MusicUpload.objects.filter(artist=artist).count()
    posts = Post.objects.filter(author=artist).count()
    products = Product.objects.filter(artist=artist, is_active=True).count()
    viewer_signal = None

    if request.user.is_authenticated:
        signal = ArtistSignal.objects.filter(
            fan=request.user,
            artist=artist,
        ).order_by("-created_at").first()
        viewer_signal = signal.signal_type if signal else None

    return {
        "id": profile.id,
        "stage_name": profile.stage_name,
        "genre": profile.genre,
        "city": profile.city,
        "artist_story": profile.artist_story,
        "influences": profile.influences,
        "is_verified": profile.is_verified,
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
        "signals": {
            "supporters": supporters,
            "tracks": tracks,
            "posts": posts,
            "products": products,
        },
        "viewer_signal": viewer_signal,
    }


def matches_filter(profile, query, location):
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

@api_view(['GET'])
def index(request):
    return Response({'app': 'discovery', 'status': 'ready'})


@api_view(["GET"])
def artist_recommendations(request):
    query = (request.query_params.get("q") or "").strip().lower()
    location = (request.query_params.get("location") or "").strip().lower()
    backfill = (request.query_params.get("backfill") or "").lower() in {"1", "true", "yes"}

    profiles = ArtistProfile.objects.select_related("owner").order_by("-created_at")
    results = []
    seen_profile_ids = set()
    skipped_count = 0

    for profile in profiles:
        if not matches_filter(profile, query, location):
            continue

        if request.user.is_authenticated and ArtistSignal.objects.filter(
            fan=request.user,
            artist=profile.owner,
            signal_type=ArtistSignal.SKIP,
        ).exists():
            skipped_count += 1

        if add_result(results, profile, request):
            seen_profile_ids.add(profile.id)

    if backfill and len(results) < 3 and (query or location):
        for profile in profiles:
            if profile.id in seen_profile_ids:
                continue

            if add_result(results, profile, request, relaxed=True):
                seen_profile_ids.add(profile.id)

            if len(results) >= 3:
                break

    results.sort(
        key=lambda artist: (
            not artist["relaxed_match"],
            artist["discovery_score"],
            artist["signals"]["supporters"],
            artist["signals"]["tracks"] + artist["signals"]["posts"],
            artist["id"],
        ),
        reverse=True,
    )

    return Response({
        "results": results,
        "count": len(results),
        "personalized": request.user.is_authenticated,
        "skipped_count": skipped_count,
    })


@api_view(["GET"])
def saved_artists(request):
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
