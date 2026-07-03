import json

from django.conf import settings

from .models import PushSubscription


def send_web_push(user, *, title, body="", target_url=""):
    if not settings.WEBPUSH_VAPID_PRIVATE_KEY:
        return 0

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        return 0

    payload = json.dumps({
        "title": title[:120],
        "body": body[:240],
        "url": target_url or settings.FRONTEND_URL,
    })
    sent = 0
    for subscription in PushSubscription.objects.filter(user=user):
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=payload,
                vapid_private_key=settings.WEBPUSH_VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.WEBPUSH_VAPID_SUBJECT},
            )
            sent += 1
        except WebPushException:
            subscription.delete()
    return sent


def deliver_push_for_notification(notification):
    return send_web_push(
        notification.recipient,
        title=notification.title,
        body=notification.body,
        target_url=notification.target_url,
    )
