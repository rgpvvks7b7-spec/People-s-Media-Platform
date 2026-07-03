import secrets

from artists.models import FanJourneyEvent


def effective_ticket_inventory(booking):
    if booking.ticket_inventory > 0:
        return booking.ticket_inventory
    if booking.listing.capacity > 0:
        return booking.listing.capacity
    return None


def tickets_sold_for_product(product_id):
    if not product_id:
        return 0
    return FanJourneyEvent.objects.filter(
        event_type=FanJourneyEvent.PURCHASE,
        metadata__product_id=product_id,
    ).count()


def ticket_availability_for_booking(booking):
    if not booking.ticket_product_id:
        return {
            "inventory": None,
            "sold": 0,
            "remaining": None,
            "sold_out": False,
        }

    inventory = effective_ticket_inventory(booking)
    sold = tickets_sold_for_product(booking.ticket_product_id)
    if inventory is None:
        return {
            "inventory": None,
            "sold": sold,
            "remaining": None,
            "sold_out": False,
        }

    remaining = max(inventory - sold, 0)
    return {
        "inventory": inventory,
        "sold": sold,
        "remaining": remaining,
        "sold_out": remaining <= 0,
    }


def ticket_is_available(booking):
    availability = ticket_availability_for_booking(booking)
    return not availability["sold_out"]


def ensure_check_in_token(booking):
    if booking.check_in_token:
        return booking.check_in_token
    booking.check_in_token = secrets.token_urlsafe(16)
    booking.save(update_fields=["check_in_token", "updated_at"])
    return booking.check_in_token
