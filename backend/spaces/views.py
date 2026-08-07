from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, throttle_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from config.throttling import UploadRateThrottle

from artistcalendar.models import ArtistCalendarItem
from artists.business_health import get_artist_business_health
from marketplace.models import Product
from notifications.models import Notification
from subscriptions.models import FanSubscription
from .availability import validate_booking_window
from .local_draw import local_supporter_counts, resolve_local_city
from .models import HostProfile, SpaceBooking, SpaceBookingReview, SpaceListing, SpaceListingPhoto
from .services import link_ticket_product, on_booking_confirmed, sync_booking_calendar_item


User = get_user_model()

MAX_SPACE_PHOTOS = 8
MAX_IMAGE_SIZE = 8 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SERIES_MAX_DATES = 12


def request_bool(data, field, default=False):
    value = data.get(field, default)
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def parse_datetime_value(value, field):
    parsed = parse_datetime(str(value or ""))
    if not parsed:
        return None, f"{field} must be a valid datetime."
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed, ""


def parse_int(value, default=0, minimum=0, maximum=None):
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = default
    result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def parse_decimal(value, default="0"):
    try:
        return Decimal(str(value if value not in {"", None} else default))
    except Exception:
        return Decimal(default)


def parse_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def normalize_material_url(value):
    url = str(value or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    if len(url) > 500:
        return None
    return url


def parse_booking_material(request):
    material_url = normalize_material_url(request.data.get("material_url"))
    if material_url is None:
        return None, None, "Material link must be a valid http or https URL."
    material_credit = str(request.data.get("material_credit") or "").strip()[:200]
    return material_url, material_credit, ""


def parse_booking_date_slots(request):
    """Return list of (starts_at, ends_at) pairs for a single show or series."""
    raw_dates = request.data.get("dates")
    slots = []

    if isinstance(raw_dates, list) and raw_dates:
        if len(raw_dates) > SERIES_MAX_DATES:
            return None, f"A series can include at most {SERIES_MAX_DATES} dates."
        for index, entry in enumerate(raw_dates):
            if not isinstance(entry, dict):
                return None, "Each series date must include starts_at and ends_at."
            starts_at, starts_error = parse_datetime_value(entry.get("starts_at"), f"dates[{index}].starts_at")
            ends_at, ends_error = parse_datetime_value(entry.get("ends_at"), f"dates[{index}].ends_at")
            if starts_error or ends_error:
                return None, starts_error or ends_error
            slots.append((starts_at, ends_at))
    else:
        starts_at, starts_error = parse_datetime_value(request.data.get("starts_at"), "starts_at")
        ends_at, ends_error = parse_datetime_value(request.data.get("ends_at"), "ends_at")
        if starts_error or ends_error:
            return None, starts_error or ends_error
        slots.append((starts_at, ends_at))

    for starts_at, ends_at in slots:
        if ends_at <= starts_at:
            return None, "ends_at must be after starts_at."

    slots.sort(key=lambda pair: pair[0])
    return slots, ""


def parse_available_windows(value):
    if isinstance(value, list):
        normalized = []
        for item in value:
            if isinstance(item, dict):
                start = str(item.get("start") or "").strip()
                end = str(item.get("end") or "").strip()
                date = str(item.get("date") or "").strip()
                if date and start and end:
                    normalized.append({"date": date, "start": start, "end": end})
                    continue
                day = str(item.get("day") or "").strip().lower()[:3]
                if day and start and end:
                    normalized.append({"day": day, "start": start, "end": end})
            elif str(item or "").strip():
                normalized.append(str(item).strip())
        return normalized

    raw = str(value or "").strip()
    if not raw:
        return []

    if raw.startswith("["):
        import json
        try:
            return parse_available_windows(json.loads(raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

    return parse_list(raw)


def validate_image_upload(file_obj, label="Photo"):
    if not file_obj:
        return None
    name = file_obj.name.lower()
    if not any(name.endswith(ext) for ext in ALLOWED_IMAGE_EXTENSIONS):
        return f"{label} must be JPG, PNG, or WEBP."
    if file_obj.size > MAX_IMAGE_SIZE:
        return f"{label} is too large (max 8MB)."
    return None


def normalize_photo_type(value):
    value = (value or SpaceListingPhoto.ROOM_OVERVIEW).strip()
    if value in dict(SpaceListingPhoto.PHOTO_TYPES):
        return value
    return SpaceListingPhoto.OTHER


def serialize_photo(photo, request):
    return {
        "id": photo.id,
        "url": request.build_absolute_uri(photo.image.url) if photo.image else None,
        "photo_type": photo.photo_type,
        "photo_type_label": photo.get_photo_type_display(),
        "caption": photo.caption,
        "sort_order": photo.sort_order,
    }


def listing_photo_queryset(listing):
    return listing.gallery_photos.all()


def save_listing_photos(listing, request):
    files = request.FILES.getlist("photos")
    if not files:
        return ""

    existing_count = listing.gallery_photos.count()
    if existing_count + len(files) > MAX_SPACE_PHOTOS:
        return f"Each listing can include up to {MAX_SPACE_PHOTOS} photos."

    types = request.data.getlist("photo_types") if hasattr(request.data, "getlist") else parse_list(request.data.get("photo_types"))
    captions = request.data.getlist("photo_captions") if hasattr(request.data, "getlist") else parse_list(request.data.get("photo_captions"))

    for index, image in enumerate(files):
        error = validate_image_upload(image, f"Photo {index + 1}")
        if error:
            return error

        SpaceListingPhoto.objects.create(
            listing=listing,
            image=image,
            photo_type=normalize_photo_type(types[index] if index < len(types) else SpaceListingPhoto.ROOM_OVERVIEW),
            caption=(captions[index] if index < len(captions) else "")[:180],
            sort_order=existing_count + index,
        )
    return ""


def serialize_host_profile(profile):
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "business_name": profile.business_name,
        "contact_email": profile.contact_email,
        "phone": profile.phone,
        "address": profile.address,
        "city": profile.city,
        "verified": profile.verified,
        "pending_ticket_earnings": str(profile.pending_ticket_earnings),
        "payouts_ready": bool(profile.stripe_connect_onboarded_at),
    }


def serialize_listing(listing, request):
    host_profile = getattr(listing.host, "host_profile", None)
    return {
        "id": listing.id,
        "host_id": listing.host_id,
        "host_username": listing.host.username,
        "host_business_name": host_profile.business_name if host_profile else listing.host.display_name,
        "name": listing.name,
        "description": listing.description,
        "photos": [serialize_photo(photo, request) for photo in listing_photo_queryset(listing)],
        "address": listing.address,
        "city": listing.city,
        "capacity": listing.capacity,
        "available_windows": listing.available_windows,
        "tags": listing.tags,
        "bar_open": listing.bar_open,
        "kitchen_open": listing.kitchen_open,
        "kitchen_notes": listing.kitchen_notes,
        "drink_minimum": listing.drink_minimum,
        "last_call": listing.last_call,
        "split_type": listing.split_type,
        "host_cut_percent": listing.host_cut_percent,
        "flat_fee_amount": str(listing.flat_fee_amount),
        "booking_mode": listing.booking_mode,
        "min_local_supporters": listing.min_local_supporters,
        "status": listing.status,
        "can_edit": request.user.is_authenticated and request.user == listing.host,
        "created_at": listing.created_at,
    }


def calendar_item_id_for(booking):
    if not booking:
        return None
    item = ArtistCalendarItem.objects.filter(space_booking_id=booking.id).values_list("id", flat=True).first()
    return item


def serialize_booking(booking, request):
    from .ticket_admission import stub_stats_for_booking, verified_admission_count
    from .ticket_inventory import ticket_availability_for_booking

    availability = ticket_availability_for_booking(booking)
    ticket_product = booking.ticket_product if booking.ticket_product_id else None
    payload = {
        "id": booking.id,
        "listing": serialize_listing(booking.listing, request),
        "artist_id": booking.artist_id,
        "artist_username": booking.artist.username,
        "artist_name": getattr(getattr(booking.artist, "artist_profile", None), "stage_name", booking.artist.username),
        "starts_at": booking.starts_at,
        "ends_at": booking.ends_at,
        "expected_audience": booking.expected_audience,
        "pitch": booking.pitch,
        "material_url": booking.material_url,
        "material_credit": booking.material_credit,
        "status": booking.status,
        "linked_event_id": booking.linked_event_id,
        "series_id": str(booking.series_id) if booking.series_id else None,
        "ticket_product_id": booking.ticket_product_id,
        "ticket_title": ticket_product.title if ticket_product else "",
        "ticket_price": str(ticket_product.price) if ticket_product else None,
        "ticket_inventory": booking.ticket_inventory,
        "tickets_sold": availability["sold"],
        "tickets_capacity": availability["inventory"],
        "tickets_remaining": availability["remaining"],
        "tickets_sold_out": availability["sold_out"],
        "attendance_checked_in": booking.attendance_checked_in,
        "check_in_count": booking.check_ins.count(),
        "tickets_verified_at_door": verified_admission_count(booking),
        "cover_charge": str(booking.ticket_price),
        "calendar_item_id": calendar_item_id_for(booking),
        "created_at": booking.created_at,
    }
    if request.user.is_authenticated and request.user.user_type == User.HOST and booking.listing.host_id == request.user.id:
        payload["artist_local_draw"] = draw_profile_for_artist(
            booking.artist,
            venue_city=booking.listing.city,
        )
        payload.update(stub_stats_for_booking(booking))
    if request.user.is_authenticated:
        payload["my_reviews"] = {
            review.reviewee_type: {
                "rating": review.rating,
                "comment": review.comment,
            }
            for review in booking.reviews.all()
            if review.reviewer_id == request.user.id
        }
    return payload


def assign_listing_fields(listing, request):
    name = (request.data.get("name") or listing.name or "").strip()
    if not name:
        return "Listing name is required."

    split_type = request.data.get("split_type") or listing.split_type or SpaceListing.DOOR_PERCENT
    if split_type not in dict(SpaceListing.SPLIT_TYPES):
        return "Invalid split type."

    booking_mode = request.data.get("booking_mode") or listing.booking_mode or SpaceListing.REQUEST
    if booking_mode not in dict(SpaceListing.BOOKING_MODES):
        return "Invalid booking mode."

    listing.name = name[:160]
    if "description" in request.data:
        listing.description = (request.data.get("description") or "").strip()
    if "address" in request.data:
        listing.address = (request.data.get("address") or "").strip()
    if "city" in request.data:
        listing.city = (request.data.get("city") or "").strip()
    if not listing.city:
        return "City is required."
    if not listing.address:
        return "Address is required."
    if not listing.description:
        return "Description is required."
    if "capacity" in request.data:
        listing.capacity = parse_int(request.data.get("capacity"), default=listing.capacity or 20, minimum=1, maximum=2000)
    if "available_windows" in request.data:
        listing.available_windows = parse_available_windows(request.data.get("available_windows"))
    if not listing.available_windows:
        return "Add at least one availability window."
    if "tags" in request.data:
        listing.tags = parse_list(request.data.get("tags"))
    if "bar_open" in request.data:
        listing.bar_open = request_bool(request.data, "bar_open", listing.bar_open)
    if "kitchen_open" in request.data:
        listing.kitchen_open = request_bool(request.data, "kitchen_open", listing.kitchen_open)
    if "kitchen_notes" in request.data:
        listing.kitchen_notes = (request.data.get("kitchen_notes") or "").strip()[:255]
    if "drink_minimum" in request.data:
        listing.drink_minimum = (request.data.get("drink_minimum") or "").strip()[:120]
    if "last_call" in request.data:
        listing.last_call = (request.data.get("last_call") or "").strip()[:80]
    listing.split_type = split_type
    if "host_cut_percent" in request.data:
        listing.host_cut_percent = parse_int(request.data.get("host_cut_percent"), default=listing.host_cut_percent or 20, minimum=0, maximum=100)
    if "flat_fee_amount" in request.data:
        listing.flat_fee_amount = parse_decimal(request.data.get("flat_fee_amount"))
    listing.booking_mode = booking_mode
    if "min_local_supporters" in request.data:
        listing.min_local_supporters = parse_int(request.data.get("min_local_supporters"), default=listing.min_local_supporters or 0, minimum=0, maximum=10000)
    if "status" in request.data and request.data.get("status") in dict(SpaceListing.STATUSES):
        listing.status = request.data.get("status")
    elif not listing.status:
        listing.status = SpaceListing.DRAFT
    return ""


@api_view(["GET", "POST"])
def host_profile(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    if request.user.user_type != User.HOST:
        return Response({"error": "Host account required"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "POST":
        profile, _ = HostProfile.objects.get_or_create(
            user=request.user,
            defaults={"business_name": request.user.display_name or request.user.username},
        )
        profile.business_name = (request.data.get("business_name") or profile.business_name).strip()[:160]
        if not profile.business_name:
            return Response({"error": "Business name is required."}, status=status.HTTP_400_BAD_REQUEST)
        profile.contact_email = (request.data.get("contact_email") or request.user.email or "").strip()
        if not profile.contact_email:
            return Response({"error": "Contact email is required."}, status=status.HTTP_400_BAD_REQUEST)
        profile.phone = (request.data.get("phone") or "").strip()[:40]
        profile.address = (request.data.get("address") or "").strip()[:255]
        if not profile.address:
            return Response({"error": "Venue address is required."}, status=status.HTTP_400_BAD_REQUEST)
        profile.city = (request.data.get("city") or "").strip()[:80]
        if not profile.city:
            return Response({"error": "Venue city is required."}, status=status.HTTP_400_BAD_REQUEST)
        profile.save()

    profile, _ = HostProfile.objects.get_or_create(
        user=request.user,
        defaults={"business_name": request.user.display_name or request.user.username},
    )
    return Response({"profile": serialize_host_profile(profile)})


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
@throttle_classes([UploadRateThrottle])
def listings(request):
    if request.method == "GET":
        queryset = SpaceListing.objects.select_related("host", "host__host_profile").prefetch_related("gallery_photos")
        if request.user.is_authenticated and request.user.user_type == User.HOST and request.query_params.get("mine"):
            queryset = queryset.filter(host=request.user)
        else:
            queryset = queryset.filter(status=SpaceListing.LIVE)
        city = (request.query_params.get("city") or "").strip()
        tag = (request.query_params.get("tag") or "").strip()
        if city:
            queryset = queryset.filter(city__icontains=city)
        results = [serialize_listing(item, request) for item in queryset[:100]]
        if tag:
            results = [item for item in results if tag in item["tags"]]
        return Response({"results": results, "count": len(results)})

    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    if request.user.user_type != User.HOST:
        return Response({"error": "Host account required"}, status=status.HTTP_403_FORBIDDEN)

    HostProfile.objects.get_or_create(
        user=request.user,
        defaults={"business_name": request.user.display_name or request.user.username},
    )
    listing = SpaceListing(host=request.user)
    error = assign_listing_fields(listing, request)
    if error:
        return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
    listing.save()
    photo_error = save_listing_photos(listing, request)
    if photo_error:
        listing.delete()
        return Response({"error": photo_error}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"message": "Space listing saved.", "listing": serialize_listing(listing, request)}, status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def listing_detail(request, listing_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    if request.user.user_type != User.HOST:
        return Response({"error": "Host account required"}, status=status.HTTP_403_FORBIDDEN)

    try:
        listing = SpaceListing.objects.get(id=listing_id, host=request.user)
    except SpaceListing.DoesNotExist:
        return Response({"error": "Space listing not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        listing.delete()
        return Response({"message": "Space listing deleted."})

    error = assign_listing_fields(listing, request)
    if error:
        return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
    listing.save()
    photo_error = save_listing_photos(listing, request)
    if photo_error:
        return Response({"error": photo_error}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"message": "Space listing updated.", "listing": serialize_listing(listing, request)})


@api_view(["DELETE"])
def listing_photo_detail(request, listing_id, photo_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    if request.user.user_type != User.HOST:
        return Response({"error": "Host account required"}, status=status.HTTP_403_FORBIDDEN)

    try:
        photo = SpaceListingPhoto.objects.select_related("listing").get(
            id=photo_id,
            listing_id=listing_id,
            listing__host=request.user,
        )
    except SpaceListingPhoto.DoesNotExist:
        return Response({"error": "Photo not found"}, status=status.HTTP_404_NOT_FOUND)

    photo.image.delete(save=False)
    photo.delete()
    return Response({"message": "Photo removed."})


@api_view(["GET", "POST"])
def bookings(request):
    if request.method == "GET":
        if not request.user.is_authenticated:
            return Response({"results": [], "count": 0})
        queryset = SpaceBooking.objects.select_related("listing", "listing__host", "artist", "ticket_product").prefetch_related("check_ins", "reviews")
        if request.user.user_type == User.HOST:
            queryset = queryset.filter(listing__host=request.user, dismissed_by_host_at__isnull=True)
        elif request.user.user_type == User.ARTIST:
            queryset = queryset.filter(artist=request.user, dismissed_by_artist_at__isnull=True)
        else:
            queryset = queryset.none()
        return Response({"results": [serialize_booking(item, request) for item in queryset[:100]], "count": queryset.count()})

    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    try:
        listing = SpaceListing.objects.get(id=request.data.get("listing_id"), status=SpaceListing.LIVE)
    except SpaceListing.DoesNotExist:
        return Response({"error": "Space listing not found"}, status=status.HTTP_404_NOT_FOUND)

    slots, slots_error = parse_booking_date_slots(request)
    if slots_error:
        return Response({"error": slots_error}, status=status.HTTP_400_BAD_REQUEST)

    for starts_at, ends_at in slots:
        window_error = validate_booking_window(listing, starts_at, ends_at)
        if window_error:
            return Response({"error": window_error}, status=status.HTTP_400_BAD_REQUEST)

    material_url, material_credit, material_error = parse_booking_material(request)
    if material_error:
        return Response({"error": material_error}, status=status.HTTP_400_BAD_REQUEST)

    local_draw = draw_profile_for_artist(request.user, venue_city=listing.city)
    if listing.min_local_supporters > 0 and local_draw["local_supporters"] < listing.min_local_supporters:
        return Response({
            "error": (
                f"This venue requires at least {listing.min_local_supporters} local supporters "
                f"in {listing.city}. You currently have {local_draw['local_supporters']}."
            ),
        }, status=status.HTTP_400_BAD_REQUEST)

    series_id = uuid4() if len(slots) > 1 else None
    expected_audience = parse_int(request.data.get("expected_audience"), default=0, minimum=0, maximum=2000)
    pitch = (request.data.get("pitch") or "").strip()
    ticket_price = parse_decimal(request.data.get("ticket_price"), default="15.00")
    booking_status = SpaceBooking.CONFIRMED if listing.booking_mode == SpaceListing.INSTANT_BOOK else SpaceBooking.REQUESTED
    linked_event_id = request.data.get("linked_event_id") or None
    ticket_product_id = request.data.get("ticket_product_id")
    publish_to_calendar = request_bool(request.data, "publish_to_calendar", True)
    calendar_visibility = request.data.get("calendar_visibility") or "public"

    linked_product = None
    if ticket_product_id:
        try:
            linked_product = Product.objects.get(id=ticket_product_id, artist=request.user, is_active=True)
        except Product.DoesNotExist:
            linked_product = None

    created = []
    for starts_at, ends_at in slots:
        booking = SpaceBooking.objects.create(
            listing=listing,
            artist=request.user,
            starts_at=starts_at,
            ends_at=ends_at,
            expected_audience=expected_audience,
            pitch=pitch,
            material_url=material_url,
            material_credit=material_credit,
            ticket_price=ticket_price,
            status=booking_status,
            linked_event_id=linked_event_id,
            series_id=series_id,
        )
        if linked_product:
            link_ticket_product(booking, linked_product)
        elif booking.status == SpaceBooking.CONFIRMED:
            from .services import ensure_booking_ticket_product
            ensure_booking_ticket_product(booking)
            booking.refresh_from_db()

        if booking.status == SpaceBooking.CONFIRMED and publish_to_calendar:
            on_booking_confirmed(
                booking,
                publish_to_calendar=True,
                calendar_visibility=calendar_visibility,
            )
            from notifications.gig_notifications import notify_local_supporters_for_booking

            notify_local_supporters_for_booking(booking)
        created.append(booking)

    primary = created[0]
    series_label = f" ({len(created)}-date series)" if series_id else ""
    Notification.objects.create(
        recipient=listing.host,
        actor=request.user,
        notification_type=Notification.SYSTEM,
        title=f"New booking request: {listing.name}{series_label}",
        body=primary.pitch[:240],
        target_url="/?page=spaces",
    )
    message = (
        f"Series requested ({len(created)} dates)."
        if series_id
        else "Booking requested."
    )
    return Response(
        {
            "message": message,
            "booking": serialize_booking(primary, request),
            "bookings": [serialize_booking(item, request) for item in created],
            "series_id": str(series_id) if series_id else None,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
def booking_status(request, booking_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        booking = SpaceBooking.objects.select_related("listing", "artist").get(id=booking_id, listing__host=request.user)
    except SpaceBooking.DoesNotExist:
        return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

    next_status = request.data.get("status")
    if next_status not in {SpaceBooking.CONFIRMED, SpaceBooking.CANCELLED, SpaceBooking.COMPLETED}:
        return Response({"error": "Invalid booking status."}, status=status.HTTP_400_BAD_REQUEST)

    previous_status = booking.status
    booking.status = next_status
    booking.attendance_checked_in = parse_int(request.data.get("attendance_checked_in"), default=booking.attendance_checked_in)
    booking.save(update_fields=["status", "attendance_checked_in", "updated_at"])

    if next_status == SpaceBooking.CONFIRMED and previous_status != SpaceBooking.CONFIRMED and request_bool(request.data, "publish_to_calendar", True):
        on_booking_confirmed(booking, publish_to_calendar=True, credit_challenge=True)
        from notifications.gig_notifications import notify_local_supporters_for_booking

        notify_local_supporters_for_booking(booking)

    if next_status == SpaceBooking.COMPLETED and booking.attendance_checked_in:
        sync_booking_calendar_item(booking)

    if next_status == SpaceBooking.COMPLETED and previous_status != SpaceBooking.COMPLETED:
        from .show_night import notify_post_show_review_prompts

        notify_post_show_review_prompts(booking)

    ticket_product_id = request.data.get("ticket_product_id")
    if ticket_product_id:
        try:
            product = Product.objects.get(id=ticket_product_id, artist=booking.artist, is_active=True)
            link_ticket_product(booking, product)
        except Product.DoesNotExist:
            pass
    Notification.objects.create(
        recipient=booking.artist,
        actor=request.user,
        notification_type=Notification.SYSTEM,
        title=f"Booking {next_status}: {booking.listing.name}",
        body="F&B revenue stays with the venue; IndieFund only tracks ticket/booking activity.",
        target_url="/?page=spaces",
    )
    return Response({"message": "Booking updated.", "booking": serialize_booking(booking, request)})


def draw_profile_for_artist(artist, *, venue_city=None):
    profile = getattr(artist, "artist_profile", None)
    local_city = resolve_local_city(venue_city, profile.city if profile else "")
    local_counts = local_supporter_counts(artist, local_city)
    active_subs = FanSubscription.objects.filter(artist=artist, active=True)
    past_attendance = SpaceBooking.objects.filter(
        artist=artist,
        status=SpaceBooking.COMPLETED,
    ).aggregate(total=Sum("attendance_checked_in"))["total"] or 0
    business_health = get_artist_business_health(artist, profile) if profile else {
        "followers": 0,
        "supporter_ratio": 0,
        "engagement": {"badge": "New"},
    }
    return {
        "artist_id": artist.id,
        "artist_username": artist.username,
        "followers": business_health["followers"],
        "local_city": local_counts["local_city"],
        "local_supporters": local_counts["local_supporters"],
        "active_subscribers": active_subs.count(),
        "supporter_ratio": business_health["supporter_ratio"],
        "engagement_badge": business_health["engagement"]["badge"],
        "past_gig_attendance": past_attendance,
        "notifyable_local_supporters_count": local_counts["notifyable_local_supporters_count"],
    }


@api_view(["GET"])
def draw_profile(request, artist_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    if request.user.user_type not in {User.HOST, User.ARTIST}:
        return Response({"error": "Host or artist account required"}, status=status.HTTP_403_FORBIDDEN)
    try:
        artist = User.objects.get(id=artist_id, user_type=User.ARTIST)
    except User.DoesNotExist:
        return Response({"error": "Artist not found"}, status=status.HTTP_404_NOT_FOUND)
    venue_city = request.query_params.get("venue_city") or request.query_params.get("listing_city")
    return Response(draw_profile_for_artist(artist, venue_city=venue_city))


@api_view(["POST"])
def notify_local_supporters(request, booking_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        booking = SpaceBooking.objects.select_related("listing", "artist", "artist__artist_profile").get(
            id=booking_id,
            artist=request.user,
            status=SpaceBooking.CONFIRMED,
        )
    except SpaceBooking.DoesNotExist:
        return Response({"error": "Confirmed booking not found"}, status=status.HTTP_404_NOT_FOUND)

    from notifications.gig_notifications import notify_local_supporters_for_booking

    force = request_bool(request.data, "force", False)
    result = notify_local_supporters_for_booking(booking, reminder=True, force=force)
    if result.get("skipped") and result.get("reason") == "reminder_cooldown":
        return Response({
            "error": "Local supporters were notified recently. Try again in 48 hours or pass force=true.",
            **result,
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)

    message = "Local supporters notified."
    if result.get("skipped") and result.get("reason") == "already_notified":
        message = "Local supporters were already notified for this gig."
    elif result.get("reason") == "no_local_subscribers":
        message = "No active local subscribers to notify yet."

    return Response({
        "message": message,
        "notified_count": result.get("notified_count", 0),
        "email_count": result.get("email_count", 0),
        "skipped": result.get("skipped", False),
        "reason": result.get("reason", ""),
    })


@api_view(["GET"])
def host_earnings(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    if request.user.user_type != User.HOST:
        return Response({"error": "Host account required"}, status=status.HTTP_403_FORBIDDEN)
    completed = SpaceBooking.objects.filter(listing__host=request.user, status=SpaceBooking.COMPLETED)
    return Response({
        "completed_bookings": completed.count(),
        "attendance_checked_in": sum(item.attendance_checked_in for item in completed),
        "policy": "IndieFund does not take a cut of food and beverage revenue. F&B stays with the venue.",
    })


def serialize_review(review):
    return {
        "id": review.id,
        "booking_id": review.booking_id,
        "reviewer_username": review.reviewer.username,
        "reviewee_type": review.reviewee_type,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at,
    }


@api_view(["GET", "POST"])
def booking_reviews(request, booking_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        booking = SpaceBooking.objects.select_related("listing", "artist").get(id=booking_id)
    except SpaceBooking.DoesNotExist:
        return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

    is_host = request.user == booking.listing.host
    is_artist = request.user == booking.artist
    owns_ticket = False
    if request.user.is_authenticated and booking.ticket_product_id:
        from marketplace.purchase_flow import fan_already_purchased_product

        owns_ticket = fan_already_purchased_product(request.user, booking.ticket_product_id)
    is_fan = owns_ticket and not is_host and not is_artist

    if not is_host and not is_artist and not is_fan and request.user.user_type != User.ADMIN:
        return Response({"error": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        reviews = SpaceBookingReview.objects.filter(booking=booking).select_related("reviewer")
        return Response({
            "results": [serialize_review(item) for item in reviews],
            "count": reviews.count(),
        })

    if booking.status != SpaceBooking.COMPLETED:
        return Response({"error": "Reviews are available after the gig is completed."}, status=status.HTTP_400_BAD_REQUEST)

    reviewee_type = request.data.get("reviewee_type")
    if is_host and reviewee_type != SpaceBookingReview.ARTIST:
        return Response({"error": "Hosts can only review the artist."}, status=status.HTTP_400_BAD_REQUEST)
    if is_artist and reviewee_type != SpaceBookingReview.HOST:
        return Response({"error": "Artists can only review the venue host."}, status=status.HTTP_400_BAD_REQUEST)
    if is_fan and reviewee_type != SpaceBookingReview.SHOW:
        return Response({"error": "Fans can review the overall show experience."}, status=status.HTTP_400_BAD_REQUEST)
    if not is_host and not is_artist and not is_fan:
        return Response({"error": "Invalid review target for this account."}, status=status.HTTP_400_BAD_REQUEST)

    rating = parse_int(request.data.get("rating"), default=5, minimum=1, maximum=5)
    review, _ = SpaceBookingReview.objects.update_or_create(
        booking=booking,
        reviewer=request.user,
        reviewee_type=reviewee_type,
        defaults={
            "rating": rating,
            "comment": (request.data.get("comment") or "").strip()[:1000],
        },
    )
    return Response({"message": "Review saved.", "review": serialize_review(review)}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def booking_check_in(request, booking_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        booking = SpaceBooking.objects.select_related("listing", "artist", "ticket_product").get(
            id=booking_id,
            status=SpaceBooking.CONFIRMED,
        )
    except SpaceBooking.DoesNotExist:
        return Response({"error": "Show not found or not open for check-in."}, status=status.HTTP_404_NOT_FOUND)

    if not booking.ticket_product_id:
        return Response({"error": "This show has no ticket to check in with."}, status=status.HTTP_400_BAD_REQUEST)

    from .ticket_admission import redeem_stub_check_in

    result, error = redeem_stub_check_in(
        booking,
        request.user,
        request.data.get("stub_code"),
    )
    if error:
        status_code = status.HTTP_403_FORBIDDEN if "Ticket required" in error else status.HTTP_400_BAD_REQUEST
        return Response({"error": error}, status=status_code)

    return Response(result)


@api_view(["POST"])
def create_booking_ticket_stub(request, booking_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    if request.user.user_type != User.HOST:
        return Response({"error": "Host account required."}, status=status.HTTP_403_FORBIDDEN)

    try:
        booking = SpaceBooking.objects.select_related("listing", "artist", "ticket_product").get(
            id=booking_id,
            listing__host=request.user,
            status=SpaceBooking.CONFIRMED,
        )
    except SpaceBooking.DoesNotExist:
        return Response({"error": "Show not found."}, status=status.HTTP_404_NOT_FOUND)

    if not booking.ticket_product_id:
        return Response({"error": "This show has no tickets."}, status=status.HTTP_400_BAD_REQUEST)

    from .ticket_admission import create_ticket_stub, stub_stats_for_booking

    stub = create_ticket_stub(booking, request.user)
    stats = stub_stats_for_booking(booking)
    return Response({
        "message": "Ticket stub ready — tell the guest this code at the door.",
        "stub_code": stub.stub_code,
        "booking_id": booking.id,
        **stats,
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def clear_bookings(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    scope = (request.data.get("scope") or "all").strip().lower()
    now = timezone.now()

    if request.user.user_type == User.HOST:
        queryset = SpaceBooking.objects.filter(listing__host=request.user, dismissed_by_host_at__isnull=True)
        if scope == "history":
            queryset = queryset.exclude(status=SpaceBooking.REQUESTED)
        elif scope != "all":
            return Response({"error": "Invalid clear scope."}, status=status.HTTP_400_BAD_REQUEST)
        cleared = queryset.update(dismissed_by_host_at=now)
    elif request.user.user_type == User.ARTIST:
        if scope not in {"all", "history"}:
            return Response({"error": "Invalid clear scope."}, status=status.HTTP_400_BAD_REQUEST)
        cleared = SpaceBooking.objects.filter(
            artist=request.user,
            dismissed_by_artist_at__isnull=True,
        ).update(dismissed_by_artist_at=now)
    else:
        return Response({"error": "Host or artist account required."}, status=status.HTTP_403_FORBIDDEN)

    return Response({"message": "Booking list cleared.", "cleared": cleared})


@api_view(["POST"])
def dismiss_booking(request, booking_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        booking = SpaceBooking.objects.select_related("listing", "artist").get(id=booking_id)
    except SpaceBooking.DoesNotExist:
        return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

    now = timezone.now()
    if request.user.user_type == User.HOST and booking.listing.host_id == request.user.id:
        booking.dismissed_by_host_at = now
        booking.save(update_fields=["dismissed_by_host_at", "updated_at"])
    elif request.user.user_type == User.ARTIST and booking.artist_id == request.user.id:
        booking.dismissed_by_artist_at = now
        booking.save(update_fields=["dismissed_by_artist_at", "updated_at"])
    else:
        return Response({"error": "You cannot remove this booking from your list."}, status=status.HTTP_403_FORBIDDEN)

    return Response({"message": "Removed from your list."})

