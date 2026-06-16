from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from .models import MusicUpload
from subscriptions.models import FanSubscription

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


def has_access(user, artist):
    if user.is_authenticated and user == artist:
        return True

    if not user.is_authenticated:
        return False

    return FanSubscription.objects.filter(
        fan=user,
        artist=artist,
        active=True,
    ).exists()

@api_view(["GET"])
def music_list(request):
    tracks = MusicUpload.objects.select_related("artist").order_by("-created_at")

    data = []
    for track in tracks:
        can_access = (not track.is_subscriber_only) or has_access(request.user, track.artist)
        data.append({
            "id": track.id,
            "title": track.title,
            "artist_username": track.artist.username,
            "genre": track.genre,
            "bpm": track.bpm,
            "is_downloadable": track.is_downloadable,
            "is_subscriber_only": track.is_subscriber_only,
            "can_access": can_access,
            "access_message": "" if can_access else "Supporters only",
            "audio_file": request.build_absolute_uri(track.audio_file.url) if track.audio_file and can_access else None,
            "cover_art": request.build_absolute_uri(track.cover_art.url) if track.cover_art else None,
            "created_at": track.created_at,
        })

    return Response(data)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
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

    cover_art = request.FILES.get("cover_art")
    cover_error = validate_upload(cover_art, ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_SIZE, "Cover art")
    if cover_error:
        return Response({"error": cover_error}, status=status.HTTP_400_BAD_REQUEST)

    track = MusicUpload.objects.create(
        artist=request.user,
        title=request.data.get("title", "Untitled Track"),
        genre=request.data.get("genre", ""),
        bpm=request.data.get("bpm") or None,
        cover_art=cover_art,
        audio_file=audio_file,
        is_downloadable=request.data.get("is_downloadable") == "true",
        is_subscriber_only=request.data.get("is_subscriber_only") == "true",
    )

    return Response({
        "message": "Track uploaded",
        "id": track.id,
        "title": track.title,
    }, status=status.HTTP_201_CREATED)
