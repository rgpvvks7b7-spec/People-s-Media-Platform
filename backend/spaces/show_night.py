from artists.models import FanJourneyEvent
from notifications.models import Notification


def notify_post_show_review_prompts(booking):
    if not booking.ticket_product_id:
        return 0

    fan_ids = (
        FanJourneyEvent.objects
        .filter(
            event_type=FanJourneyEvent.PURCHASE,
            metadata__product_id=booking.ticket_product_id,
        )
        .values_list("fan_id", flat=True)
        .distinct()
    )
    profile = getattr(booking.artist, "artist_profile", None)
    stage_name = profile.stage_name if profile else booking.artist.username
    notifications = []
    for fan_id in fan_ids:
        notifications.append(Notification(
            recipient_id=fan_id,
            actor=booking.artist,
            notification_type=Notification.SYSTEM,
            title=f"How was {stage_name} @ {booking.listing.name}?",
            body="Leave a quick show review while it's fresh.",
            target_url=f"/?page=spaces&review_booking={booking.id}",
        ))

    if notifications:
        Notification.objects.bulk_create(notifications)
    return len(notifications)
