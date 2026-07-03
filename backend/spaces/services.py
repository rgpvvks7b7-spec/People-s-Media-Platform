from decimal import Decimal

from django.db.models import F
from django.utils import timezone

from artistcalendar.models import ArtistCalendarItem
from challenges.services import increment_metric
from config.platform_fees import split_ticket_sale
from marketplace.models import Product

DEFAULT_TICKET_PRICE = Decimal("15.00")


def sync_booking_calendar_item(booking, *, visibility=None):
    """Create or update a public gig calendar item when a booking is confirmed."""
    if booking.status not in {booking.CONFIRMED, booking.COMPLETED}:
        return None

    profile = getattr(booking.artist, "artist_profile", None)
    profession = profile.profession_list()[0] if profile else "music"
    venue_name = booking.listing.name
    host_name = getattr(getattr(booking.listing.host, "host_profile", None), "business_name", booking.listing.host.username)
    title = f"Live at {venue_name}"
    description_parts = [
        f"Hosted at {host_name}.",
        booking.pitch.strip() if booking.pitch else "",
    ]
    if booking.listing.bar_open:
        description_parts.append("Bar open during show.")
    if booking.listing.kitchen_open:
        description_parts.append("Kitchen open during show.")
    description = " ".join(part for part in description_parts if part)

    visibility_map = {
        "private": ArtistCalendarItem.PRIVATE,
        "supporters": ArtistCalendarItem.SUPPORTERS,
        "public": ArtistCalendarItem.PUBLIC,
    }
    resolved_visibility = visibility_map.get(visibility, visibility or ArtistCalendarItem.PUBLIC)
    if resolved_visibility not in dict(ArtistCalendarItem.VISIBILITY_CHOICES):
        resolved_visibility = ArtistCalendarItem.PUBLIC

    item = (
        ArtistCalendarItem.objects.filter(space_booking=booking).first()
        or ArtistCalendarItem(artist=booking.artist, space_booking=booking)
    )
    item.profession = profession
    item.title = title[:160]
    item.description = description[:2000]
    item.starts_at = booking.starts_at
    item.ends_at = booking.ends_at
    item.item_type = ArtistCalendarItem.GIG
    item.visibility = resolved_visibility
    item.save()
    return item


def ticket_listing_for_product(product):
    from .models import SpaceBooking

    booking = (
        SpaceBooking.objects
        .select_related("listing")
        .filter(ticket_product=product, status=SpaceBooking.CONFIRMED)
        .order_by("starts_at")
        .first()
    )
    return booking.listing if booking else None


def link_ticket_product(booking, product):
    if not product or product.artist_id != booking.artist_id:
        return booking
    booking.ticket_product = product
    booking.linked_event_id = product.id
    booking.save(update_fields=["ticket_product", "linked_event_id", "updated_at"])
    product.save()
    return booking


def booking_ticket_price(booking):
    if booking.ticket_price is not None and booking.ticket_price >= 0:
        return booking.ticket_price
    return DEFAULT_TICKET_PRICE


def ensure_booking_ticket_product(booking):
    if booking.status not in {booking.CONFIRMED, booking.COMPLETED}:
        return None

    if booking.ticket_product_id:
        product = booking.ticket_product
        if product and product.is_active:
            product.save()
            return product

    profile = getattr(booking.artist, "artist_profile", None)
    stage_name = profile.stage_name if profile else booking.artist.username
    venue_name = booking.listing.name
    price = booking_ticket_price(booking)
    artist_share, platform_fee, host_share = split_ticket_sale(price, booking.listing)

    product = Product(
        artist=booking.artist,
        profession=profile.profession_list()[0] if profile else "music",
        product_type=Product.EVENT_TICKET,
        title=f"{stage_name} @ {venue_name}",
        description="Show ticket — tap I'm here when you arrive.",
        price=price,
        artist_share=artist_share,
        platform_fee=platform_fee,
        host_share=host_share,
        is_active=True,
    )
    product.save()
    link_ticket_product(booking, product)
    booking.refresh_from_db()
    return product


def credit_host_ticket_share(listing, host_share, booking_id):
    host_share = Decimal(str(host_share))
    if host_share <= 0 or listing is None:
        return

    from .models import HostProfile

    host_profile, _ = HostProfile.objects.get_or_create(
        user=listing.host,
        defaults={"business_name": listing.host.display_name or listing.host.username},
    )
    HostProfile.objects.filter(pk=host_profile.pk).update(
        pending_ticket_earnings=F("pending_ticket_earnings") + host_share,
    )


def on_booking_confirmed(booking, *, publish_to_calendar=True, calendar_visibility=None, credit_challenge=True):
    from .ticket_inventory import ensure_check_in_token

    ensure_check_in_token(booking)
    ensure_booking_ticket_product(booking)
    if publish_to_calendar:
        sync_booking_calendar_item(booking, visibility=calendar_visibility or ArtistCalendarItem.PUBLIC)
    if credit_challenge:
        increment_metric(booking.artist, "spaces_booking")


def average_review_rating(booking, reviewee_type):
    from .models import SpaceBookingReview

    ratings = SpaceBookingReview.objects.filter(
        booking=booking,
        reviewee_type=reviewee_type,
    ).values_list("rating", flat=True)
    if not ratings:
        return None
    return round(sum(ratings) / len(ratings), 2)
