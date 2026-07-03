import secrets

from django.db import IntegrityError
from django.utils import timezone

STUB_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
STUB_CODE_LENGTH = 6


def normalize_stub_code(value):
    return (value or "").strip().upper().replace(" ", "")


def generate_stub_code():
    return "".join(secrets.choice(STUB_CODE_ALPHABET) for _ in range(STUB_CODE_LENGTH))


def ensure_ticket_admission(fan, product, booking):
    from .models import ShowTicketAdmission

    existing = ShowTicketAdmission.objects.filter(booking=booking, fan=fan).first()
    if existing:
        return existing

    return ShowTicketAdmission.objects.create(
        booking=booking,
        fan=fan,
        product=product,
    )


def get_ticket_admission(fan, product_id, booking=None):
    from .models import ShowTicketAdmission

    queryset = ShowTicketAdmission.objects.filter(fan=fan, product_id=product_id)
    if booking is not None:
        queryset = queryset.filter(booking=booking)
    return queryset.select_related("booking").first()


def admission_for_purchase(fan, product_id):
    from marketplace.models import Product
    from marketplace.purchase_flow import fan_already_purchased_product

    from .models import SpaceBooking

    admission = get_ticket_admission(fan, product_id)
    if admission:
        return admission
    if not fan_already_purchased_product(fan, product_id):
        return None
    booking = (
        SpaceBooking.objects
        .filter(ticket_product_id=product_id, status=SpaceBooking.CONFIRMED)
        .order_by("starts_at")
        .first()
    )
    if not booking:
        return None
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return None
    return ensure_ticket_admission(fan, product, booking)


def create_ticket_stub(booking, host_user):
    from .models import ShowTicketStub

    for _ in range(12):
        try:
            return ShowTicketStub.objects.create(
                booking=booking,
                created_by=host_user,
                stub_code=generate_stub_code(),
            )
        except IntegrityError:
            continue
    raise RuntimeError("Could not allocate a unique ticket stub code.")


def redeem_stub_check_in(booking, fan, stub_code):
    from marketplace.purchase_flow import fan_already_purchased_product

    from .models import ShowCheckIn, ShowTicketStub

    normalized = normalize_stub_code(stub_code)
    if not normalized:
        return None, "Enter the code staff gave you at the door."

    if not fan_already_purchased_product(fan, booking.ticket_product_id):
        return None, "Ticket required to check in."

    try:
        stub = ShowTicketStub.objects.select_related("booking").get(
            booking=booking,
            stub_code=normalized,
        )
    except ShowTicketStub.DoesNotExist:
        return None, "That code is not valid for this show."

    if stub.redeemed_at:
        if stub.redeemed_by_id == fan.id:
            check_in = ShowCheckIn.objects.filter(booking=booking, fan=fan).first()
            return {
                "message": "You are already checked in.",
                "checked_in": True,
                "checked_in_at": check_in.checked_in_at if check_in else stub.redeemed_at,
                "attendance_checked_in": booking.attendance_checked_in,
            }, ""
        return None, "That code was already used."

    now = timezone.now()
    stub.redeemed_by = fan
    stub.redeemed_at = now
    stub.save(update_fields=["redeemed_by", "redeemed_at"])

    admission = admission_for_purchase(fan, booking.ticket_product_id)
    if admission and not admission.host_verified_at:
        admission.host_verified_at = now
        admission.host_verified_by = booking.listing.host
        admission.save(update_fields=["host_verified_at", "host_verified_by"])

    check_in, _created = ShowCheckIn.objects.get_or_create(booking=booking, fan=fan)
    booking.attendance_checked_in = booking.check_ins.count()
    booking.save(update_fields=["attendance_checked_in", "updated_at"])

    return {
        "message": "Checked in. Enjoy the show!",
        "checked_in": True,
        "checked_in_at": check_in.checked_in_at,
        "attendance_checked_in": booking.attendance_checked_in,
    }, ""


def verified_admission_count(booking):
    from .models import ShowCheckIn

    return ShowCheckIn.objects.filter(booking=booking).count()


def stub_stats_for_booking(booking):
    from .models import ShowTicketStub

    stubs = ShowTicketStub.objects.filter(booking=booking)
    return {
        "stubs_issued": stubs.count(),
        "stubs_redeemed": stubs.filter(redeemed_at__isnull=False).count(),
        "stubs_available": stubs.filter(redeemed_at__isnull=True).count(),
    }


def enrich_show_fan_check_in(show, booking, user):
    from marketplace.purchase_flow import fan_already_purchased_product

    from .models import ShowCheckIn, SpaceBooking

    if not user or not getattr(user, "is_authenticated", False) or not booking.ticket_product_id:
        return show

    owns_ticket = fan_already_purchased_product(user, booking.ticket_product_id)
    checked_in = ShowCheckIn.objects.filter(booking=booking, fan=user).exists()
    has_ended = show.get("has_ended") or booking.status == SpaceBooking.COMPLETED or (
        booking.ends_at is not None and booking.ends_at < timezone.now()
    )
    show["owns_ticket"] = owns_ticket
    show["checked_in"] = checked_in
    show["can_check_in"] = owns_ticket and booking.status == SpaceBooking.CONFIRMED and not checked_in and not has_ended
    return show
