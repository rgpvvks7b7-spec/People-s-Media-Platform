from datetime import timezone as dt_timezone

from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from artists.models import ArtistProfile
from posts.views import is_supporter
from .models import ArtistCalendarItem


def normalize_profession(user, value):
    profession = (value or ArtistProfile.DEFAULT_PROFESSION).strip()
    if profession not in ArtistProfile.valid_profession_keys():
        return None

    if user.is_authenticated and user.user_type == "artist":
        try:
            if user.artist_profile.has_profession(profession):
                return profession
        except ArtistProfile.DoesNotExist:
            pass

    return None


def parse_datetime_value(value, field):
    if not value:
        return None, f"{field} is required."

    parsed = parse_datetime(str(value))
    if not parsed:
        return None, f"{field} must be a valid datetime."

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())

    return parsed, ""


def parse_optional_datetime_value(value, field):
    if not value:
        return None, ""
    return parse_datetime_value(value, field)


def parse_early_hours(value):
    try:
        hours = int(value or 0)
    except (TypeError, ValueError):
        hours = 0
    return max(0, min(hours, 24 * 30))


def can_view_calendar_item(user, item):
    if user.is_authenticated and user == item.artist:
        return True

    if item.visibility == ArtistCalendarItem.PRIVATE:
        return False

    supporter = is_supporter(user, item.artist, item.profession)
    if item.visibility == ArtistCalendarItem.SUPPORTERS:
        return supporter

    if item.visibility == ArtistCalendarItem.PUBLIC:
        if supporter or item.supporter_early_hours <= 0:
            return True
        return timezone.now() >= item.starts_at

    return False


def serialize_calendar_item(item, request):
    return {
        "id": item.id,
        "artist_id": item.artist_id,
        "artist_username": item.artist.username,
        "profession": item.profession,
        "profession_label": ArtistProfile.profession_label(item.profession),
        "title": item.title,
        "description": item.description,
        "starts_at": item.starts_at,
        "ends_at": item.ends_at,
        "item_type": item.item_type,
        "item_type_label": dict(ArtistCalendarItem.ITEM_TYPES).get(item.item_type, "Other"),
        "visibility": item.visibility,
        "supporter_early_hours": item.supporter_early_hours,
        "music_upload_id": item.music_upload_id,
        "live_session_id": item.live_session_id,
        "space_booking_id": item.space_booking_id,
        "venue_name": item.space_booking.listing.name if item.space_booking_id and getattr(item.space_booking, "listing", None) else "",
        "venue_city": item.space_booking.listing.city if item.space_booking_id and getattr(item.space_booking, "listing", None) else "",
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "can_edit": request.user.is_authenticated and request.user == item.artist,
    }


def assign_calendar_fields(item, request):
    title = (request.data.get("title") or "").strip()
    if not title:
        return "Title is required."

    starts_at, starts_error = parse_datetime_value(request.data.get("starts_at"), "starts_at")
    if starts_error:
        return starts_error

    ends_at, ends_error = parse_optional_datetime_value(request.data.get("ends_at"), "ends_at")
    if ends_error:
        return ends_error

    if ends_at and ends_at < starts_at:
        return "ends_at must be after starts_at."

    profession = normalize_profession(request.user, request.data.get("profession"))
    if not profession:
        return "Artist does not offer this profession"

    item_type = request.data.get("item_type") or ArtistCalendarItem.OTHER
    if item_type not in dict(ArtistCalendarItem.ITEM_TYPES):
        return "Invalid calendar item type."

    visibility = request.data.get("visibility") or ArtistCalendarItem.PRIVATE
    if visibility not in dict(ArtistCalendarItem.VISIBILITY_CHOICES):
        return "Invalid calendar visibility."

    item.profession = profession
    item.title = title[:160]
    item.description = (request.data.get("description") or "").strip()
    item.starts_at = starts_at
    item.ends_at = ends_at
    item.item_type = item_type
    item.visibility = visibility
    item.supporter_early_hours = parse_early_hours(request.data.get("supporter_early_hours"))
    item.music_upload_id = request.data.get("music_upload_id") or None
    item.live_session_id = request.data.get("live_session_id") or None
    return ""


@api_view(["GET", "POST"])
def calendar_items(request):
    if request.method == "GET":
        artist_id = request.query_params.get("artist_id")
        profession = request.query_params.get("profession")

        items = ArtistCalendarItem.objects.select_related(
            "artist",
            "space_booking",
            "space_booking__listing",
        ).filter(
            starts_at__gte=timezone.now() - timezone.timedelta(days=1)
        )
        if artist_id:
            items = items.filter(artist_id=artist_id)
        elif request.user.is_authenticated and request.user.user_type == "artist":
            items = items.filter(artist=request.user)
        if profession:
            items = items.filter(profession=profession)

        visible_items = [
            item for item in items.order_by("starts_at")[:100]
            if can_view_calendar_item(request.user, item)
        ]
        return Response({
            "results": [serialize_calendar_item(item, request) for item in visible_items],
            "count": len(visible_items),
        })

    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != "artist":
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    item = ArtistCalendarItem(artist=request.user)
    error = assign_calendar_fields(item, request)
    if error:
        return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    item.save()
    from challenges.services import increment_metric
    increment_metric(request.user, "calendar_item")

    announced = 0
    announce_requested = request.data.get("announce_drop") in {True, "true", "1", "on"}
    if (
        announce_requested
        and item.item_type == ArtistCalendarItem.RELEASE
        and item.visibility != ArtistCalendarItem.PRIVATE
        and item.starts_at > timezone.now()
    ):
        from .drops import announce_drop

        announced = announce_drop(item)

    message = "Calendar item saved."
    if announced:
        message = f"Drop scheduled and announced to {announced} supporter{'s' if announced != 1 else ''}."
    return Response({
        "message": message,
        "item": serialize_calendar_item(item, request),
        "announced": announced,
    }, status=status.HTTP_201_CREATED)


@api_view(["PATCH", "POST"])
def calendar_item_detail(request, item_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        item = ArtistCalendarItem.objects.get(id=item_id, artist=request.user)
    except ArtistCalendarItem.DoesNotExist:
        return Response({"error": "Calendar item not found"}, status=status.HTTP_404_NOT_FOUND)

    error = assign_calendar_fields(item, request)
    if error:
        return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    item.save()
    from challenges.services import increment_metric
    increment_metric(request.user, "calendar_item")
    return Response({
        "message": "Calendar item updated.",
        "item": serialize_calendar_item(item, request),
    })


@api_view(["GET"])
def calendar_feed(request):
    artist_id = request.query_params.get("artist_id")
    items = ArtistCalendarItem.objects.select_related("artist").filter(
        visibility=ArtistCalendarItem.PUBLIC,
        starts_at__gte=timezone.now() - timezone.timedelta(days=1),
    )
    if artist_id:
        items = items.filter(artist_id=artist_id)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//IndieFund//Artist Calendar//EN",
    ]
    for item in items.order_by("starts_at")[:100]:
        start_utc = item.starts_at.astimezone(dt_timezone.utc)
        end_line = []
        if item.ends_at:
            end_utc = item.ends_at.astimezone(dt_timezone.utc)
            end_line = [f"DTEND:{end_utc.strftime('%Y%m%dT%H%M%SZ')}"]
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:indiefund-calendar-{item.id}",
            f"SUMMARY:{item.title}",
            f"DTSTART:{start_utc.strftime('%Y%m%dT%H%M%SZ')}",
            *end_line,
            f"DESCRIPTION:{item.description}",
            "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    return HttpResponse("\r\n".join(lines), content_type="text/calendar")
