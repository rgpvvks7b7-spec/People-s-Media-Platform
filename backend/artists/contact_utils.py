from django.utils import timezone

from .journey import log_fan_journey_event
from .models import ArtistFanContact, FanJourneyEvent


def request_bool(data, field, default=False):
    value = data.get(field, default)
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def sync_artist_fan_contact(fan, artist, source=ArtistFanContact.SIGNUP_OPT_IN, explicit_share=False):
    if not fan or not artist or fan == artist:
        return None

    should_share = bool(explicit_share or fan.share_email_with_supported_artists)
    contact, _ = ArtistFanContact.objects.get_or_create(
        fan=fan,
        artist=artist,
        defaults={"source": source},
    )

    if should_share and fan.email:
        was_shared = contact.email_shared
        contact.share(source)
        contact.save(update_fields=["email_shared", "shared_at", "revoked_at", "source", "updated_at"])
        if not was_shared:
            log_fan_journey_event(FanJourneyEvent.EMAIL_OPT_IN, artist, fan=fan, metadata={"source": source})
        return contact

    return contact


def revoke_artist_fan_contact(fan, artist):
    contact = ArtistFanContact.objects.filter(fan=fan, artist=artist).first()
    if contact and contact.email_shared:
        contact.revoke()
        contact.save(update_fields=["email_shared", "revoked_at", "updated_at"])
    return contact


def update_global_email_consent(user, share_email):
    user.share_email_with_supported_artists = bool(share_email)
    if share_email and not user.email_share_consent_at:
        user.email_share_consent_at = timezone.now()
    if not share_email:
        user.email_share_consent_at = None
        ArtistFanContact.objects.filter(fan=user, email_shared=True).update(
            email_shared=False,
            revoked_at=timezone.now(),
        )
    user.save(update_fields=["share_email_with_supported_artists", "email_share_consent_at"])

    if share_email:
        from subscriptions.models import FanSubscription

        supported_artists = (
            FanSubscription.objects
            .select_related("artist")
            .filter(fan=user, active=True)
        )
        seen_artist_ids = set()
        for subscription in supported_artists:
            if subscription.artist_id in seen_artist_ids:
                continue
            seen_artist_ids.add(subscription.artist_id)
            sync_artist_fan_contact(
                user,
                subscription.artist,
                source=ArtistFanContact.MANUAL,
            )
