from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from notifications.models import Notification
from subscriptions.models import FanSubscription

from .models import LiveChatMessage, LiveSession


def serialize_message(message):
    return {
        "id": message.id,
        "author_username": message.author.username,
        "author_display": message.author.display_name or message.author.username,
        "author_role": "Artist" if message.author.user_type == "artist" else "Fan",
        "body": message.body,
        "created_at": message.created_at,
    }


def serialize_session(session, include_messages=False):
    data = {
        "id": session.id,
        "artist_id": session.artist.id,
        "artist_username": session.artist.username,
        "title": session.title,
        "description": session.description,
        "access_mode": session.access_mode,
        "is_live": session.is_live,
        "viewer_count": session.viewer_count,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
    }
    if include_messages:
        data["messages"] = [
            serialize_message(message)
            for message in session.messages.select_related("author").order_by("created_at")
        ]
    return data


@api_view(["GET"])
def session_list(request):
    sessions = LiveSession.objects.select_related("artist").filter(is_live=True)
    return Response({"results": [serialize_session(session) for session in sessions]})


@api_view(["POST"])
def start_session(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != "artist":
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    LiveSession.objects.filter(artist=request.user, is_live=True).update(is_live=False, ended_at=timezone.now())
    session = LiveSession.objects.create(
        artist=request.user,
        title=request.data.get("title") or "Live session",
        description=request.data.get("description", ""),
        access_mode=request.data.get("access_mode") or LiveSession.PREVIEW_30,
    )

    supporters = FanSubscription.objects.select_related("fan").filter(artist=request.user, active=True)
    for sub in supporters:
        Notification.objects.create(
            recipient=sub.fan,
            actor=request.user,
            notification_type=Notification.LIVE,
            title=f"{request.user.display_name or request.user.username} is live",
            body=session.title,
            target_url="/live",
        )

    from challenges.services import increment_metric
    increment_metric(request.user, "go_live")

    return Response({"message": "Live started", "session": serialize_session(session, include_messages=True)}, status=status.HTTP_201_CREATED)


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

    return Response({"message": "Live stopped", "session": serialize_session(session, include_messages=True)})


@api_view(["GET", "POST"])
def chat_messages(request, session_id):
    try:
        session = LiveSession.objects.get(id=session_id)
    except LiveSession.DoesNotExist:
        return Response({"error": "Live session not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response({
            "session": serialize_session(session),
            "messages": [
                serialize_message(message)
                for message in session.messages.select_related("author").order_by("created_at")
            ],
        })

    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    body = (request.data.get("body") or "").strip()
    if not body:
        return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

    message = LiveChatMessage.objects.create(session=session, author=request.user, body=body)
    return Response({"message": serialize_message(message)}, status=status.HTTP_201_CREATED)
