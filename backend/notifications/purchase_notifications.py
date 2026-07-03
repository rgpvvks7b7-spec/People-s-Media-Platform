from artists.models import ArtistProfile
from notifications.models import Notification
from notifications.services import notify_artist_sale, notify_fan_purchase, notify_new_supporter


def notify_subscription_started(fan, artist, *, profession, monthly_amount, payment_provider="demo"):
    profession_label = ArtistProfile.profession_label(profession)
    notify_fan_purchase(
        fan,
        artist,
        title=f"Now supporting {artist.username}",
        body=f"${monthly_amount}/mo · {profession_label}",
        target_url=f"/?artist={artist.username}",
        notification_type=Notification.SUPPORTER,
    )
    notify_new_supporter(
        artist,
        fan,
        profession=profession,
        monthly_amount=monthly_amount,
        payment_provider=payment_provider,
    )


def notify_payment_failed(subscription):
    from django.conf import settings
    from notifications.models import Notification

    profession_label = ArtistProfile.profession_label(subscription.profession)
    notify_fan_purchase(
        subscription.fan,
        subscription.artist,
        title="Payment failed — update billing",
        body=f"Your ${subscription.monthly_amount}/mo support for {subscription.artist.username} ({profession_label}) needs a new payment method.",
        target_url=f"{settings.FRONTEND_URL}/?page=profile",
        notification_type=Notification.SYSTEM,
    )
    Notification.objects.create(
        recipient=subscription.artist,
        actor=subscription.fan,
        notification_type=Notification.SYSTEM,
        title=f"Supporter payment failed ({subscription.fan.username})",
        body=f"{profession_label} · ${subscription.monthly_amount}/mo — Stripe will retry or cancel the subscription.",
        target_url=f"/?artist={subscription.artist.username}",
    )
