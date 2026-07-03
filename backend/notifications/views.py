from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Notification, PushSubscription
from .push import deliver_push_for_notification


def serialize_notification(notification):
    return {
        "id": notification.id,
        "type": notification.notification_type,
        "title": notification.title,
        "body": notification.body,
        "target_url": notification.target_url,
        "actor_username": notification.actor.username if notification.actor else "",
        "read": notification.read_at is not None,
        "read_at": notification.read_at,
        "created_at": notification.created_at,
    }


@api_view(["GET"])
def notification_list(request):
    if not request.user.is_authenticated:
        return Response({"results": [], "unread_count": 0})

    notifications = Notification.objects.select_related("actor").filter(recipient=request.user)[:50]
    unread_count = Notification.objects.filter(recipient=request.user, read_at__isnull=True).count()

    return Response({
        "results": [serialize_notification(notification) for notification in notifications],
        "unread_count": unread_count,
    })


@api_view(["POST"])
def mark_read(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    notification_id = request.data.get("id")
    qs = Notification.objects.filter(recipient=request.user, read_at__isnull=True)
    if notification_id:
        qs = qs.filter(id=notification_id)

    updated = qs.update(read_at=timezone.now())
    return Response({"message": "Notifications updated", "updated": updated})


@api_view(["POST"])
def clear_notifications(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    notification_id = request.data.get("id")
    qs = Notification.objects.filter(recipient=request.user)
    if notification_id:
        qs = qs.filter(id=notification_id)

    deleted, _ = qs.delete()
    unread_count = Notification.objects.filter(recipient=request.user, read_at__isnull=True).count()
    return Response({
        "message": "Notifications cleared",
        "deleted": deleted,
        "unread_count": unread_count,
    })


@api_view(["GET"])
def push_vapid_public_key(request):
    from django.conf import settings

    return Response({
        "public_key": settings.WEBPUSH_VAPID_PUBLIC_KEY,
        "enabled": bool(settings.WEBPUSH_VAPID_PUBLIC_KEY and settings.WEBPUSH_VAPID_PRIVATE_KEY),
    })


@api_view(["POST"])
def push_subscribe(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    subscription = request.data.get("subscription") or {}
    endpoint = subscription.get("endpoint")
    keys = subscription.get("keys") or {}
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not endpoint or not p256dh or not auth:
        return Response({"error": "Invalid push subscription payload"}, status=status.HTTP_400_BAD_REQUEST)

    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "user": request.user,
            "p256dh": p256dh,
            "auth": auth,
            "user_agent": (request.META.get("HTTP_USER_AGENT") or "")[:255],
        },
    )
    return Response({"message": "Push notifications enabled"})


@api_view(["POST"])
def push_unsubscribe(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    endpoint = (request.data.get("endpoint") or "").strip()
    if endpoint:
        PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
    else:
        PushSubscription.objects.filter(user=request.user).delete()
    return Response({"message": "Push notifications disabled"})
