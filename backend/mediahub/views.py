from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, throttle_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from django.http import FileResponse, Http404
from django.utils import timezone
from artists.journey import log_fan_journey_event
from config.media_access import build_stream_url, parse_media_stream_token
from config.throttling import UploadRateThrottle
from .models import ArtworkUpload, FanPlaylist, FanPlaylistTrack, MusicUpload, SongCoverArt
from artists.models import ArtistProfile, FanJourneyEvent
from livehub.services import party_grants_full_access
from subscriptions.models import FanSubscription
from originlock.services import (
    approvals_for,
    compute_file_sha256,
    create_pending_approval,
    get_approval_for,
    origin_badges,
    serialize_origin_lock,
)
from originlock.models import MediaAccessLog, ReleaseApproval
from originlock.protection import (
    compute_acoustic_fingerprint,
    log_media_access,
    serialize_protection,
)

_UNSET = object()

MAX_AUDIO_SIZE = 50 * 1024 * 1024
MAX_IMAGE_SIZE = 8 * 1024 * 1024
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def validate_upload(file_obj, allowed_extensions, max_size, label):
    if not file_obj:
        return None

    name = file_obj.name.lower()
    if not any(name.endswith(ext) for ext in allowed_extensions):
        return f"{label} must be one of: {', '.join(sorted(allowed_extensions))}"

    if file_obj.size > max_size:
        return f"{label} is too large."

    return None


def normalize_profession(user, value):
    profession = (value or ArtistProfile.DEFAULT_PROFESSION).strip()
    if profession not in ArtistProfile.valid_profession_keys():
        return None

    if user.is_authenticated and user.user_type == "artist":
        try:
            if user.artist_profile.has_profession(profession):
                return profession
        except ArtistProfile.DoesNotExist:
            pass

    return None


def has_access(user, artist, profession):
    if user.is_authenticated and user == artist:
        return True

    if not user.is_authenticated:
        return False

    return FanSubscription.objects.filter(
        fan=user,
        artist=artist,
        profession=profession,
        active=True,
    ).exists()


def parse_preview_seconds(value):
    try:
        seconds = int(value or 30)
    except (TypeError, ValueError):
        seconds = 30
    return max(10, min(seconds, 120))


def validate_ai_disclosure(level, note):
    level = (level or MusicUpload.HUMAN_MADE).strip()
    note = (note or "").strip()

    if level not in dict(MusicUpload.AI_DISCLOSURE_CHOICES):
        return None, note, "Invalid AI disclosure level."

    if level == MusicUpload.AI_GENERATED:
        return None, note, "Fully AI-generated tracks aren’t permitted on IndieFund."

    if level != MusicUpload.HUMAN_MADE and not note:
        return None, note, "AI disclosure note is required for assisted or collaborative tracks."

    if len(note) > 500:
        return None, note, "AI disclosure note must be 500 characters or fewer."

    return level, note, ""


def resolve_track_cover_url(track, request):
    if track.cover_art:
        return request.build_absolute_uri(track.cover_art.url)
    if track.library_cover_id and track.library_cover.image:
        return request.build_absolute_uri(track.library_cover.image.url)
    return None


def serialize_song_cover(cover, request):
    return {
        "id": cover.id,
        "label": cover.label,
        "profession": cover.profession,
        "profession_label": ArtistProfile.profession_label(cover.profession),
        "image": request.build_absolute_uri(cover.image.url) if cover.image else None,
        "is_default": cover.is_default,
        "created_at": cover.created_at,
    }


def resolve_track_audio_url(track, request, access):
    if not track.audio_file:
        return None
    # Never hand out raw /media/ URLs. Every track streams through the signed,
    # expiring token endpoint so access can be revoked and gated on approval.
    return build_stream_url(request, track.id, access)


def serialize_track(track, request, approval=_UNSET):
    from artistcalendar.drops import drop_access_message, drop_lock_state

    if approval is _UNSET:
        approval = get_approval_for(track)

    is_owner = request.user.is_authenticated and request.user == track.artist
    released = approval is None or approval.approval_status == ReleaseApproval.APPROVED
    show_files = released or is_owner

    can_access = (not track.is_subscriber_only) or has_access(request.user, track.artist, track.profession)
    can_preview = bool(track.is_subscriber_only and track.preview_enabled and track.audio_file)
    drop_state = drop_lock_state(track, request.user)
    drop_message = ""
    if drop_state and not drop_state["unlocked"]:
        can_access = False
        can_preview = bool(track.preview_enabled and track.audio_file)
        drop_message = drop_access_message(drop_state)
    stream_allowed = track.public_stream_enabled or is_owner
    audio_url = resolve_track_audio_url(track, request, "full") if stream_allowed else None
    preview_url = resolve_track_audio_url(track, request, "preview") if stream_allowed else None
    release_status = approval.approval_status if approval else ReleaseApproval.APPROVED
    badges = origin_badges(approval)
    payload = {
        "id": track.id,
        "title": track.title,
        "artist_username": track.artist.username,
        "profession": track.profession,
        "profession_label": ArtistProfile.profession_label(track.profession),
        "genre": track.genre,
        "bpm": track.bpm,
        "is_downloadable": track.is_downloadable,
        "is_subscriber_only": track.is_subscriber_only,
        "preview_enabled": track.preview_enabled,
        "preview_seconds": track.preview_seconds,
        "allow_fan_radio": track.allow_fan_radio,
        "ai_disclosure_level": track.ai_disclosure_level,
        "ai_disclosure_note": track.ai_disclosure_note,
        "ai_disclosure_badge": track.ai_disclosure_badge,
        "can_access": can_access,
        "can_preview": can_preview and not can_access and show_files,
        "can_add_to_playlist": can_access and released,
        "access_message": "" if can_access else (
            drop_message or f"Subscribe to unlock full track. Preview available for {track.preview_seconds}s."
        ),
        "drop": drop_state,
        "audio_file": audio_url if (can_access and show_files) else None,
        "preview_audio_file": preview_url if (can_preview and not can_access and show_files) else None,
        "cover_art": resolve_track_cover_url(track, request),
        "library_cover_id": track.library_cover_id,
        "created_at": track.created_at,
        "release_status": release_status,
        "origin_lock": serialize_origin_lock(approval),
        "origin_badges": badges,
        "protection": serialize_protection(track, badges=badges),
    }
    if is_owner:
        payload["funnel"] = get_track_funnel_metrics(track)
    return payload


def get_track_funnel_metrics(track):
    preview_count = FanJourneyEvent.objects.filter(
        music_upload=track,
        event_type=FanJourneyEvent.MUSIC_PREVIEW,
    ).count()
    full_play_count = FanJourneyEvent.objects.filter(
        music_upload=track,
        event_type=FanJourneyEvent.MUSIC_FULL_PLAY,
    ).count()
    converted_fan_ids = set()
    first_listens = {}
    for event in FanJourneyEvent.objects.filter(
        music_upload=track,
        event_type__in=[FanJourneyEvent.MUSIC_PREVIEW, FanJourneyEvent.MUSIC_FULL_PLAY],
        fan__isnull=False,
    ).order_by("fan_id", "occurred_at"):
        first_listens.setdefault(event.fan_id, event.occurred_at)
    for fan_id, first_listen_at in first_listens.items():
        if FanJourneyEvent.objects.filter(
            artist=track.artist,
            fan_id=fan_id,
            event_type=FanJourneyEvent.SUBSCRIBE,
            occurred_at__gte=first_listen_at,
            occurred_at__lte=first_listen_at + timezone.timedelta(days=7),
        ).exists():
            converted_fan_ids.add(fan_id)
    return {
        "preview_plays": preview_count,
        "full_plays": full_play_count,
        "subscriber_conversions_7d": len(converted_fan_ids),
    }


def serialize_playlist(playlist, request):
    tracks = [
        serialize_track(item.track, request)
        for item in playlist.playlist_tracks.select_related("track", "track__artist").all()
    ]
    return {
        "id": playlist.id,
        "title": playlist.title,
        "description": playlist.description,
        "is_public": playlist.is_public,
        "track_count": len(tracks),
        "tracks": tracks,
        "created_at": playlist.created_at,
        "updated_at": playlist.updated_at,
    }

@api_view(["GET"])
def music_list(request):
    tracks = list(MusicUpload.objects.select_related("artist", "library_cover").order_by("-created_at"))
    approvals = approvals_for(MusicUpload, [track.id for track in tracks])
    data = []
    for track in tracks:
        approval = approvals.get(track.id)
        is_owner = request.user.is_authenticated and request.user == track.artist
        released = approval is None or approval.approval_status == ReleaseApproval.APPROVED
        if not released and not is_owner:
            continue
        data.append(serialize_track(track, request, approval=approval))
    return Response(data)


@api_view(["GET"])
def fan_radio_tracks(request):
    tracks = list(MusicUpload.objects.select_related("artist").filter(allow_fan_radio=True).order_by("-created_at"))
    approvals = approvals_for(MusicUpload, [track.id for track in tracks])
    data = []
    for track in tracks:
        approval = approvals.get(track.id)
        released = approval is None or approval.approval_status == ReleaseApproval.APPROVED
        if not released:
            continue
        payload = serialize_track(track, request, approval=approval)
        if payload["audio_file"]:
            data.append(payload)
    return Response({"results": data, "count": len(data)})


@api_view(["POST"])
def record_music_event(request):
    event_type = request.data.get("event_type")
    if event_type not in {FanJourneyEvent.MUSIC_PREVIEW, FanJourneyEvent.MUSIC_FULL_PLAY}:
        return Response({"error": "Invalid music event type"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        track = MusicUpload.objects.select_related("artist").get(id=request.data.get("track_id"))
    except MusicUpload.DoesNotExist:
        return Response({"error": "Track not found"}, status=status.HTTP_404_NOT_FOUND)

    track_payload = serialize_track(track, request)
    if not track_payload["audio_file"] and not (
        event_type == FanJourneyEvent.MUSIC_PREVIEW and track_payload["preview_audio_file"]
    ):
        return Response({"error": "You need access to this track before playback is tracked."}, status=status.HTTP_403_FORBIDDEN)

    event = log_fan_journey_event(
        event_type,
        track.artist,
        fan=request.user if request.user.is_authenticated else None,
        music_upload=track,
        metadata={
            "track_id": track.id,
            "source": request.data.get("source") or "player",
            "seconds_played": request.data.get("seconds_played") or 0,
        },
    )

    if event_type == FanJourneyEvent.MUSIC_FULL_PLAY and request.user.is_authenticated:
        try:
            from promotions.models import Campaign
            from promotions.services import charge_engagement

            charge_engagement(Campaign.TRACK, track.id, request.user, "full_listen")
        except Exception:
            pass

    return Response({
        "message": "Music event recorded.",
        "event_id": event.id if event else None,
        "track_id": track.id,
        "event_type": event_type,
    }, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def fan_playlists(request):
    if not request.user.is_authenticated:
        return Response({"results": [], "count": 0, "authenticated": False})

    if request.method == "GET":
        playlists = FanPlaylist.objects.filter(owner=request.user).prefetch_related("playlist_tracks__track__artist")
        data = [serialize_playlist(playlist, request) for playlist in playlists]
        return Response({"results": data, "count": len(data), "authenticated": True})

    title = (request.data.get("title") or "").strip()
    if not title:
        return Response({"error": "Playlist title is required"}, status=status.HTTP_400_BAD_REQUEST)

    playlist = FanPlaylist.objects.create(
        owner=request.user,
        title=title[:120],
        description=(request.data.get("description") or "").strip(),
        is_public=request.data.get("is_public") in {True, "true", "1", "on"},
    )

    return Response({
        "message": "Playlist created",
        "playlist": serialize_playlist(playlist, request),
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def add_playlist_track(request, playlist_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        playlist = FanPlaylist.objects.get(id=playlist_id, owner=request.user)
    except FanPlaylist.DoesNotExist:
        return Response({"error": "Playlist not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        track = MusicUpload.objects.select_related("artist").get(id=request.data.get("track_id"))
    except MusicUpload.DoesNotExist:
        return Response({"error": "Track not found"}, status=status.HTTP_404_NOT_FOUND)

    track_payload = serialize_track(track, request)
    if not track_payload["audio_file"]:
        return Response({"error": "You need access to this track before adding it to a playlist."}, status=status.HTTP_403_FORBIDDEN)

    position = playlist.playlist_tracks.count()
    playlist_track, created = FanPlaylistTrack.objects.get_or_create(
        playlist=playlist,
        track=track,
        defaults={"position": position},
    )
    playlist.save(update_fields=["updated_at"])

    return Response({
        "created": created,
        "message": "Track added to playlist" if created else "Track is already in this playlist",
        "playlist": serialize_playlist(playlist, request),
    })


@api_view(["POST"])
def remove_playlist_track(request, playlist_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        playlist = FanPlaylist.objects.get(id=playlist_id, owner=request.user)
    except FanPlaylist.DoesNotExist:
        return Response({"error": "Playlist not found"}, status=status.HTTP_404_NOT_FOUND)

    FanPlaylistTrack.objects.filter(playlist=playlist, track_id=request.data.get("track_id")).delete()
    for position, item in enumerate(playlist.playlist_tracks.all()):
        if item.position != position:
            item.position = position
            item.save(update_fields=["position"])
    playlist.save(update_fields=["updated_at"])

    return Response({
        "message": "Track removed",
        "playlist": serialize_playlist(playlist, request),
    })


@api_view(["GET"])
def artwork_list(request):
    artworks = ArtworkUpload.objects.select_related("artist").order_by("-created_at")

    data = []
    for artwork in artworks:
        can_access = (not artwork.is_supporter_only) or has_access(request.user, artwork.artist, artwork.profession)
        data.append({
            "id": artwork.id,
            "title": artwork.title,
            "artist_username": artwork.artist.username,
            "profession": artwork.profession,
            "profession_label": ArtistProfile.profession_label(artwork.profession),
            "image": request.build_absolute_uri(artwork.image.url) if artwork.image and can_access else None,
            "description": artwork.description,
            "medium": artwork.medium,
            "dimensions": artwork.dimensions,
            "year": artwork.year,
            "availability": artwork.availability,
            "availability_label": dict(ArtworkUpload.AVAILABILITY_CHOICES).get(artwork.availability, "Available"),
            "is_supporter_only": artwork.is_supporter_only,
            "can_access": can_access,
            "access_message": "" if can_access else "Supporters only",
            "created_at": artwork.created_at,
        })

    return Response(data)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@throttle_classes([UploadRateThrottle])
def create_music(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != "artist":
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    audio_file = request.FILES.get("audio_file")
    if not audio_file:
        return Response({"error": "Audio file is required"}, status=status.HTTP_400_BAD_REQUEST)

    audio_error = validate_upload(audio_file, ALLOWED_AUDIO_EXTENSIONS, MAX_AUDIO_SIZE, "Audio file")
    if audio_error:
        return Response({"error": audio_error}, status=status.HTTP_400_BAD_REQUEST)

    profession = normalize_profession(request.user, request.data.get("profession"))
    if not profession:
        return Response({"error": "Artist does not offer this profession"}, status=status.HTTP_400_BAD_REQUEST)

    cover_art = request.FILES.get("cover_art")
    cover_error = validate_upload(cover_art, ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_SIZE, "Cover art")
    if cover_error:
        return Response({"error": cover_error}, status=status.HTTP_400_BAD_REQUEST)

    ai_disclosure_level, ai_disclosure_note, ai_error = validate_ai_disclosure(
        request.data.get("ai_disclosure_level"),
        request.data.get("ai_disclosure_note"),
    )
    if ai_error:
        return Response({"error": ai_error}, status=status.HTTP_400_BAD_REQUEST)

    from artists.trust import evaluate_upload_risk, upload_limit_for_artist

    profile = getattr(request.user, "artist_profile", None)
    remaining, limit_message = upload_limit_for_artist(request.user, profile)
    if remaining == 0:
        return Response({"error": limit_message or "Upload limit reached."}, status=status.HTTP_403_FORBIDDEN)

    library_cover = None
    library_cover_id = request.data.get("library_cover_id")
    if library_cover_id and not cover_art:
        try:
            library_cover = SongCoverArt.objects.get(
                id=library_cover_id,
                artist=request.user,
                profession=profession,
            )
        except (SongCoverArt.DoesNotExist, ValueError, TypeError):
            return Response({"error": "Saved cover art not found"}, status=status.HTTP_400_BAD_REQUEST)
    elif not cover_art:
        library_cover = SongCoverArt.objects.filter(
            artist=request.user,
            profession=profession,
            is_default=True,
        ).first()

    if cover_art and request.data.get("save_cover_to_library") in {True, "true", "1", "on"}:
        is_default = not SongCoverArt.objects.filter(artist=request.user, profession=profession).exists()
        if is_default:
            SongCoverArt.objects.filter(artist=request.user, profession=profession).update(is_default=False)
        library_cover = SongCoverArt.objects.create(
            artist=request.user,
            profession=profession,
            image=cover_art,
            label=(request.data.get("title") or "Untitled Track")[:120],
            is_default=is_default,
        )
        cover_art = None

    track = MusicUpload.objects.create(
        artist=request.user,
        profession=profession,
        title=request.data.get("title", "Untitled Track"),
        genre=request.data.get("genre", ""),
        bpm=request.data.get("bpm") or None,
        cover_art=cover_art,
        library_cover=library_cover if not cover_art else None,
        audio_file=audio_file,
        file_hash_sha256=compute_file_sha256(audio_file),
        acoustic_fingerprint=compute_acoustic_fingerprint(audio_file),
        is_downloadable=request.data.get("is_downloadable") == "true",
        is_subscriber_only=request.data.get("is_subscriber_only", "true") in {True, "true", "1", "on"},
        preview_enabled=request.data.get("preview_enabled", "true") in {True, "true", "1", "on"},
        preview_seconds=parse_preview_seconds(request.data.get("preview_seconds")),
        allow_fan_radio=request.data.get("allow_fan_radio") == "true",
        ai_disclosure_level=ai_disclosure_level,
        ai_disclosure_note=ai_disclosure_note,
    )
    evaluate_upload_risk(track)

    approval = create_pending_approval(
        request.user,
        track,
        audio_file,
        file_name=audio_file.name,
        ai_usage_status=ai_disclosure_level,
    )

    return Response({
        "message": "Track uploaded. Finalise your release to publish it.",
        "id": track.id,
        "title": track.title,
        "release_approval_id": approval.id,
        "release_status": approval.approval_status,
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def song_cover_list(request):
    if not request.user.is_authenticated or request.user.user_type != "artist":
        return Response([])

    covers = SongCoverArt.objects.filter(artist=request.user).order_by("-is_default", "-created_at")
    profession = request.query_params.get("profession")
    if profession:
        covers = covers.filter(profession=profession)

    return Response([serialize_song_cover(cover, request) for cover in covers])


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@throttle_classes([UploadRateThrottle])
def create_song_cover(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != "artist":
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    profession = normalize_profession(request.user, request.data.get("profession"))
    if not profession:
        return Response({"error": "Artist does not offer this profession"}, status=status.HTTP_400_BAD_REQUEST)

    image = request.FILES.get("image")
    if not image:
        return Response({"error": "Cover image is required"}, status=status.HTTP_400_BAD_REQUEST)

    image_error = validate_upload(image, ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_SIZE, "Cover image")
    if image_error:
        return Response({"error": image_error}, status=status.HTTP_400_BAD_REQUEST)

    is_default = request.data.get("is_default") in {True, "true", "1", "on"}
    if is_default:
        SongCoverArt.objects.filter(artist=request.user, profession=profession).update(is_default=False)

    cover = SongCoverArt.objects.create(
        artist=request.user,
        profession=profession,
        image=image,
        label=(request.data.get("label") or "").strip()[:120],
        is_default=is_default,
    )

    return Response({
        "message": "Cover art saved",
        "cover": serialize_song_cover(cover, request),
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def set_default_song_cover(request, cover_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != "artist":
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    try:
        cover = SongCoverArt.objects.get(id=cover_id, artist=request.user)
    except SongCoverArt.DoesNotExist:
        return Response({"error": "Cover art not found"}, status=status.HTTP_404_NOT_FOUND)

    SongCoverArt.objects.filter(artist=request.user, profession=cover.profession).update(is_default=False)
    cover.is_default = True
    cover.save(update_fields=["is_default"])

    return Response({
        "message": "Default cover updated",
        "cover": serialize_song_cover(cover, request),
    })


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@throttle_classes([UploadRateThrottle])
def create_artwork(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != "artist":
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    profession = normalize_profession(request.user, request.data.get("profession"))
    if not profession:
        return Response({"error": "Artist does not offer this profession"}, status=status.HTTP_400_BAD_REQUEST)

    if ArtistProfile.is_music_branch_profession(profession):
        return Response({"error": "Artwork belongs on an arts profession."}, status=status.HTTP_400_BAD_REQUEST)

    image = request.FILES.get("image")
    if not image:
        return Response({"error": "Artwork image is required"}, status=status.HTTP_400_BAD_REQUEST)

    image_error = validate_upload(image, ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_SIZE, "Artwork image")
    if image_error:
        return Response({"error": image_error}, status=status.HTTP_400_BAD_REQUEST)

    artwork = ArtworkUpload.objects.create(
        artist=request.user,
        profession=profession,
        title=request.data.get("title", "Untitled Artwork"),
        image=image,
        description=request.data.get("description", ""),
        medium=request.data.get("medium", ""),
        dimensions=request.data.get("dimensions", ""),
        year=request.data.get("year") or None,
        availability=request.data.get("availability", ArtworkUpload.AVAILABLE),
        is_supporter_only=request.data.get("is_supporter_only") == "true",
    )

    return Response({
        "message": "Artwork uploaded",
        "id": artwork.id,
        "title": artwork.title,
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def stream_track(request, track_id):
    token = request.GET.get("token", "")
    parsed_id, access = parse_media_stream_token(token)
    if parsed_id != track_id or access not in {"full", "preview"}:
        return Response({"error": "Invalid or expired stream token"}, status=status.HTTP_403_FORBIDDEN)

    try:
        track = MusicUpload.objects.select_related("artist").get(id=track_id)
    except MusicUpload.DoesNotExist:
        raise Http404

    if not track.audio_file:
        raise Http404

    is_owner = request.user.is_authenticated and request.user == track.artist
    approval = get_approval_for(track)
    released = approval is None or approval.approval_status == ReleaseApproval.APPROVED
    if not released and not is_owner:
        return Response({"error": "This release has not been finalised yet."}, status=status.HTTP_403_FORBIDDEN)

    # A live listening party unlocks its featured track for everyone allowed
    # in the room, for the duration of the party.
    party_access = access == "full" and party_grants_full_access(track, request.user)

    if not track.public_stream_enabled and not is_owner and not party_access:
        return Response({"error": "Streaming is disabled for this track."}, status=status.HTTP_403_FORBIDDEN)

    from artistcalendar.drops import drop_access_message, drop_lock_state

    drop_state = drop_lock_state(track, request.user)
    drop_locked = bool(drop_state and not drop_state["unlocked"])

    if access == "preview":
        preview_offered = (track.is_subscriber_only or drop_locked) and track.preview_enabled
        if not preview_offered:
            return Response({"error": "Preview not available"}, status=status.HTTP_403_FORBIDDEN)
    elif drop_locked and not party_access:
        return Response({"error": drop_access_message(drop_state)}, status=status.HTTP_403_FORBIDDEN)
    elif track.is_subscriber_only and not party_access and not has_access(request.user, track.artist, track.profession):
        if not (request.user.is_authenticated and request.user == track.artist):
            return Response({"error": "Subscription required"}, status=status.HTTP_403_FORBIDDEN)

    log_media_access(
        request,
        track,
        track.artist,
        MediaAccessLog.PREVIEW if access == "preview" else MediaAccessLog.STREAM,
    )

    content_type = "audio/mpeg"
    name = track.audio_file.name.lower()
    if name.endswith(".wav"):
        content_type = "audio/wav"
    elif name.endswith(".ogg"):
        content_type = "audio/ogg"
    elif name.endswith(".flac"):
        content_type = "audio/flac"
    elif name.endswith(".m4a") or name.endswith(".aac"):
        content_type = "audio/mp4"

    return FileResponse(track.audio_file.open("rb"), content_type=content_type)
