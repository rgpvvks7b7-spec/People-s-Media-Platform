from artists.models import ArtistFanContact

from .models import Notification
from .push import deliver_push_for_notification


def _create_notification(**kwargs):
    notification = Notification.objects.create(**kwargs)
    deliver_push_for_notification(notification)
    return notification


def notify_opted_in_supporters(artist, notification_type, title, body="", target_url=""):
    contacts = (
        ArtistFanContact.objects
        .select_related("fan")
        .filter(artist=artist, email_shared=True, fan__is_active=True)
    )
    notifications = []
    for contact in contacts:
        if contact.fan_id == artist.id:
            continue
        notifications.append(
            Notification(
                recipient=contact.fan,
                actor=artist,
                notification_type=notification_type,
                title=title[:180],
                body=body,
                target_url=target_url[:255],
            )
        )

    created = 0
    for notification in notifications:
        _create_notification(
            recipient=notification.recipient,
            actor=notification.actor,
            notification_type=notification.notification_type,
            title=notification.title,
            body=notification.body,
            target_url=notification.target_url,
        )
        created += 1
    return created


def notify_fan_purchase(fan, artist, *, title, body="", target_url="", notification_type=Notification.PURCHASE):
    if fan.id == artist.id:
        return None
    return _create_notification(
        recipient=fan,
        actor=artist,
        notification_type=notification_type,
        title=title[:180],
        body=body,
        target_url=target_url[:255],
    )


def notify_artist_sale(artist, fan, *, title, body="", target_url=""):
    if fan.id == artist.id:
        return None
    return _create_notification(
        recipient=artist,
        actor=fan,
        notification_type=Notification.PURCHASE,
        title=title[:180],
        body=body,
        target_url=target_url[:255],
    )


def notify_new_supporter(artist, fan, *, profession, monthly_amount, payment_provider="demo"):
    from artists.models import ArtistProfile

    profession_label = ArtistProfile.profession_label(profession)
    if fan.id == artist.id:
        return None
    return _create_notification(
        recipient=artist,
        actor=fan,
        notification_type=Notification.SUPPORTER,
        title=f"New supporter: {fan.username}",
        body=f"${monthly_amount}/mo · {profession_label} · {payment_provider}",
        target_url="/?page=profile",
    )
