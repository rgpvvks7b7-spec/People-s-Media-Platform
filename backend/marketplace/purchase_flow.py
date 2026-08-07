from decimal import Decimal

from config.platform_fees import marketplace_rate_for_artist, split_amount, split_ticket_sale
from artists.journey import log_fan_journey_event
from artists.models import FanJourneyEvent
from notifications.services import notify_artist_sale, notify_fan_purchase
from .models import Product


def fan_already_purchased_product(fan, product_id):
    return FanJourneyEvent.objects.filter(
        fan=fan,
        event_type=FanJourneyEvent.PURCHASE,
        metadata__product_id=product_id,
    ).exists()


def ticket_sale_split(product):
    if product.product_type != Product.EVENT_TICKET:
        artist_share, platform_fee = split_amount(product.price, marketplace_rate_for_artist(product.artist))
        return artist_share, platform_fee, 0

    from spaces.services import ticket_listing_for_product

    listing = ticket_listing_for_product(product)
    return split_ticket_sale(product.price, listing)


def build_purchase_receipt(product):
    amount = product.price
    artist_share, platform_fee, host_share = ticket_sale_split(product)
    receipt = {
        "product_id": product.id,
        "product_title": product.title,
        "product_type": product.product_type,
        "amount": str(amount),
        "artist_share": str(artist_share),
        "platform_fee": str(platform_fee),
        "host_share": str(host_share),
        "artist_username": product.artist.username,
        "show": None,
    }

    if product.product_type == Product.EVENT_TICKET:
        from spaces.models import SpaceBooking

        booking = (
            SpaceBooking.objects
            .select_related("listing")
            .filter(ticket_product=product, status=SpaceBooking.CONFIRMED)
            .order_by("starts_at")
            .first()
        )
        if booking:
            profile = getattr(product.artist, "artist_profile", None)
            receipt["show"] = {
                "booking_id": booking.id,
                "starts_at": booking.starts_at,
                "venue_name": booking.listing.name,
                "venue_city": booking.listing.city,
                "stage_name": profile.stage_name if profile else product.artist.username,
                "host_cut_percent": booking.listing.host_cut_percent,
                "split_type": booking.listing.split_type,
            }

    return receipt


def complete_product_purchase(fan, product, *, payment_provider="demo"):
    if product.product_type == Product.EVENT_TICKET and fan_already_purchased_product(fan, product.id):
        return None, "already_purchased"

    booking = None
    if product.product_type == Product.EVENT_TICKET:
        from spaces.models import SpaceBooking
        from spaces.ticket_inventory import ticket_is_available

        booking = (
            SpaceBooking.objects
            .select_related("listing")
            .filter(ticket_product=product, status=SpaceBooking.CONFIRMED)
            .order_by("starts_at")
            .first()
        )
        if booking and not ticket_is_available(booking):
            return None, "sold_out"

    receipt = build_purchase_receipt(product)
    if product.product_type == Product.EVENT_TICKET and booking:
        from spaces.ticket_admission import ensure_ticket_admission

        ensure_ticket_admission(fan, product, booking)

    log_fan_journey_event(
        FanJourneyEvent.PURCHASE,
        product.artist,
        fan=fan,
        metadata={
            "product_id": product.id,
            "product_type": product.product_type,
            "product_title": product.title,
            "amount": receipt["amount"],
            "artist_share": receipt["artist_share"],
            "platform_fee": receipt["platform_fee"],
            "host_share": receipt["host_share"],
            "payment_provider": payment_provider,
        },
    )

    if product.product_type == Product.EVENT_TICKET and booking and Decimal(receipt["host_share"]) > 0:
        from spaces.services import credit_host_ticket_share

        credit_host_ticket_share(booking.listing, receipt["host_share"], booking.id)

    show = receipt.get("show") or {}
    if product.product_type == Product.EVENT_TICKET and show:
        fan_title = f"Ticket confirmed: {product.title}"
        fan_body = f"{show.get('stage_name', product.artist.username)} @ {show.get('venue_name', 'venue')}"
        fan_target = f"/?page=my-scene&show={show.get('booking_id')}"
    else:
        fan_title = f"Purchase confirmed: {product.title}"
        fan_body = f"${receipt['amount']} from {product.artist.username}"
        fan_target = f"/?artist={product.artist.username}"

    notify_fan_purchase(
        fan,
        product.artist,
        title=fan_title,
        body=fan_body,
        target_url=fan_target,
    )
    notify_artist_sale(
        product.artist,
        fan,
        title=f"New sale: {product.title}",
        body=f"{fan.username} purchased · ${receipt['amount']}",
        target_url="/?page=profile",
    )

    if product.product_type == Product.EVENT_TICKET and fan.email:
        from notifications.email_delivery import send_ticket_receipt_email

        send_ticket_receipt_email(fan, product, receipt)

    try:
        from promotions.models import Campaign
        from promotions.services import charge_engagement

        charge_engagement(Campaign.PRODUCT, product.id, fan, "purchase")
    except Exception:
        pass

    receipt["payment_provider"] = payment_provider
    return receipt, ""
