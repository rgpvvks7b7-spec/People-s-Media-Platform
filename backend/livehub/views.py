from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from config.media_access import build_stream_url
from mediahub.models import MusicUpload
from notifications.models import Notification
from subscriptions.models import FanSubscription

from .models import LiveChatMessage, LiveSession
from .services import join_requirement, user_can_join


def serialize_message(message):
    return {
        "id": message.id,
        "author_username": message.author.username,
        "author_display": message.author.display_name or message.author.username,
        "author_role": "Artist" if message.author.user_type == "artist" else "Fan",
        "body": message.body,
        "created_at": message.created_at,
    }


def serialize_track_summary(track, request=None):
    if track is None:
        return None

    from mediahub.views import resolve_track_cover_url

    return {
        "id": track.id,
        "title": track.title,
        "artist_username": track.artist.username,
        "cover_art": resolve_track_cover_url(track, request) if request is not None else None,
    }


def serialize_session(session, include_messages=False, request=None):
    data = {
        "id": session.id,
        "artist_id": session.artist.id,
        "artist_username": session.artist.username,
        "artist_display": session.artist.display_name or session.artist.username,
        "title": session.title,
        "description": session.description,
        "access_mode": session.access_mode,
        "is_live": session.is_live,
        "viewer_count": session.viewer_count,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "track": serialize_track_summary(session.track, request) if session.track_id else None,
    }
    if include_messages:
        data["messages"] = [
            serialize_message(message)
            for message in session.messages.select_related("author").order_by("created_at")
        ]
    return data


@api_view(["GET"])
def session_list(request):
    sessions = LiveSession.objects.select_related("artist", "track", "track__artist").filter(is_live=True)
    return Response({"results": [serialize_session(session, request=request) for session in sessions]})


@api_view(["GET"])
def session_detail(request, session_id):
    try:
        session = LiveSession.objects.select_related("artist", "track", "track__artist").get(id=session_id)
    except LiveSession.DoesNotExist:
        return Response({"error": "Live session not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        after = int(request.GET.get("after") or 0)
    except (TypeError, ValueError):
        after = 0

    data = serialize_session(session, request=request)
    data["messages"] = [
        serialize_message(message)
        for message in session.messages.select_related("author").filter(id__gt=after).order_by("created_at")
    ]

    can_join = user_can_join(session, request.user)
    data["viewer_can_join"] = can_join
    data["join_requirement"] = join_requirement(session, request.user)
    data["is_host"] = request.user.is_authenticated and request.user == session.artist

    stream_url = None
    if can_join and session.is_live and session.track_id and session.track.audio_file:
        stream_url = build_stream_url(request, session.track_id, "full")
    data["stream_url"] = stream_url

    return Response(data)


@api_view(["POST"])
def start_session(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != "artist":
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    track = None
    track_id = request.data.get("track_id")
    if track_id:
        try:
            track = MusicUpload.objects.get(id=track_id, artist=request.user)
        except (MusicUpload.DoesNotExist, TypeError, ValueError):
            return Response({"error": "Track not found in your library"}, status=status.HTTP_400_BAD_REQUEST)
        if not track.audio_file:
            return Response({"error": "That track has no audio file to play"}, status=status.HTTP_400_BAD_REQUEST)

    LiveSession.objects.filter(artist=request.user, is_live=True).update(is_live=False, ended_at=timezone.now())
    session = LiveSession.objects.create(
        artist=request.user,
        title=request.data.get("title") or ("Listening party" if track else "Live session"),
        description=request.data.get("description", ""),
        access_mode=request.data.get("access_mode") or LiveSession.PUBLIC,
        track=track,
    )

    artist_name = request.user.display_name or request.user.username
    if track:
        notification_title = f"{artist_name} started a listening party"
        notification_body = f"{session.title} — {track.title}"
    else:
        notification_title = f"{artist_name} is live"
        notification_body = session.title

    supporters = FanSubscription.objects.select_related("fan").filter(artist=request.user, active=True)
    for sub in supporters:
        Notification.objects.create(
            recipient=sub.fan,
            actor=request.user,
            notification_type=Notification.LIVE,
            title=notification_title,
            body=notification_body,
            target_url="/?page=live",
        )

    from challenges.services import increment_metric
    increment_metric(request.user, "go_live")

    return Response({
        "message": "Listening party started" if track else "Live started",
        "session": serialize_session(session, include_messages=True, request=request),
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def stop_session(request, session_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        session = LiveSession.objects.get(id=session_id)
    except LiveSession.DoesNotExist:
        return Response({"error": "Live session not found"}, status=status.HTTP_404_NOT_FOUND)

    if session.artist != request.user:
        return Response({"error": "You can only stop your own live session"}, status=status.HTTP_403_FORBIDDEN)

    session.is_live = False
    session.ended_at = timezone.now()
    session.save(update_fields=["is_live", "ended_at"])

    return Response({"message": "Live stopped", "session": serialize_session(session, include_messages=True, request=request)})


@api_view(["GET", "POST"])
def chat_messages(request, session_id):
    try:
        session = LiveSession.objects.select_related("artist", "track", "track__artist").get(id=session_id)
    except LiveSession.DoesNotExist:
        return Response({"error": "Live session not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        try:
            after = int(request.GET.get("after") or 0)
        except (TypeError, ValueError):
            after = 0
        return Response({
            "session": serialize_session(session, request=request),
            "messages": [
                serialize_message(message)
                for message in session.messages.select_related("author").filter(id__gt=after).order_by("created_at")
            ],
        })

    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if not user_can_join(session, request.user):
        return Response({"error": "This party is for supporters only"}, status=status.HTTP_403_FORBIDDEN)

    body = (request.data.get("body") or "").strip()
    if not body:
        return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

    message = LiveChatMessage.objects.create(session=session, author=request.user, body=body)
    return Response({"message": serialize_message(message)}, status=status.HTTP_201_CREATED)
