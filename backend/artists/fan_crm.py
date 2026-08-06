"""Fan CRM: the artist-facing view of fan relationships plus segmented broadcast.

The relationship is the asset — this module unifies follows, subscriptions,
tips, purchases, and mailing consent into one list an artist can act on.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Max, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from marketplace.models import Product
from notifications.models import Notification
from notifications.services import _create_notification
from subscriptions.models import FanSubscription, OneTimeTip

from .models import ArtistFanContact, ArtistFollow, FanJourneyEvent

BROADCAST_SEGMENTS = ["all", "supporters", "followers", "ticket_buyers", "mailing_list"]
BROADCAST_COOLDOWN_HOURS = 24
FAN_LIST_LIMIT = 200


def _artist_guard(request):
    from accounts.models import User

    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)
    return None


def _blank_row(fan):
    return {
        "fan_id": fan.id,
        "fan_username": fan.username,
        "display_name": fan.display_name or fan.username,
        "location": fan.discovery_location or "",
        "is_supporter": False,
        "monthly_amount": Decimal("0.00"),
        "supporter_since": None,
        "is_follower": False,
        "follower_since": None,
        "tips_total": Decimal("0.00"),
        "tips_count": 0,
        "purchases_total": Decimal("0.00"),
        "purchases_count": 0,
        "is_ticket_buyer": False,
        "email_shared": False,
        "last_active": None,
    }


def build_fan_rows(artist):
    rows = {}

    def row_for(fan):
        if fan.id not in rows:
            rows[fan.id] = _blank_row(fan)
        return rows[fan.id]

    subscriptions = (
        FanSubscription.objects
        .select_related("fan")
        .filter(artist=artist, active=True)
    )
    for subscription in subscriptions:
        row = row_for(subscription.fan)
        row["is_supporter"] = True
        row["monthly_amount"] += subscription.monthly_amount
        if row["supporter_since"] is None or subscription.started_at < row["supporter_since"]:
            row["supporter_since"] = subscription.started_at

    for follow in ArtistFollow.objects.select_related("fan").filter(artist=artist):
        row = row_for(follow.fan)
        row["is_follower"] = True
        row["follower_since"] = follow.created_at

    tips = (
        OneTimeTip.objects
        .select_related("fan")
        .filter(artist=artist)
    )
    for tip in tips:
        row = row_for(tip.fan)
        row["tips_total"] += tip.amount
        row["tips_count"] += 1

    purchase_events = (
        FanJourneyEvent.objects
        .select_related("fan")
        .filter(artist=artist, event_type=FanJourneyEvent.PURCHASE, fan__isnull=False)
    )
    for event in purchase_events:
        row = row_for(event.fan)
        metadata = event.metadata or {}
        try:
            row["purchases_total"] += Decimal(str(metadata.get("amount") or "0"))
        except ArithmeticError:
            pass
        row["purchases_count"] += 1
        if metadata.get("product_type") == Product.EVENT_TICKET:
            row["is_ticket_buyer"] = True

    contacts = (
        ArtistFanContact.objects
        .select_related("fan")
        .filter(artist=artist, email_shared=True)
    )
    for contact in contacts:
        row_for(contact.fan)["email_shared"] = True

    last_seen = (
        FanJourneyEvent.objects
        .filter(artist=artist, fan_id__in=list(rows.keys()))
        .values("fan_id")
        .annotate(last=Max("occurred_at"))
    )
    for entry in last_seen:
        rows[entry["fan_id"]]["last_active"] = entry["last"]

    rows.pop(artist.id, None)
    return rows


def _segments_for_row(row):
    segments = []
    if row["is_supporter"]:
        segments.append("supporters")
    if row["is_follower"]:
        segments.append("followers")
    if row["is_ticket_buyer"]:
        segments.append("ticket_buyers")
    if row["email_shared"]:
        segments.append("mailing_list")
    return segments


def _row_in_segment(row, segment):
    if segment == "all":
        return True
    return segment in _segments_for_row(row)


def _lifetime_spend(row):
    return row["tips_total"] + row["purchases_total"]


def _serialize_row(row):
    return {
        **row,
        "monthly_amount": str(row["monthly_amount"].quantize(Decimal("0.01"))),
        "tips_total": str(row["tips_total"].quantize(Decimal("0.01"))),
        "purchases_total": str(row["purchases_total"].quantize(Decimal("0.01"))),
        "lifetime_spend": str(_lifetime_spend(row).quantize(Decimal("0.01"))),
        "segments": _segments_for_row(row),
    }


@api_view(["GET"])
def fan_list(request):
    blocked = _artist_guard(request)
    if blocked:
        return blocked

    segment = request.query_params.get("segment") or "all"
    if segment not in BROADCAST_SEGMENTS:
        return Response({"error": "Unknown segment"}, status=status.HTTP_400_BAD_REQUEST)

    rows = build_fan_rows(request.user)
    counts = {name: 0 for name in BROADCAST_SEGMENTS}
    counts["all"] = len(rows)
    for row in rows.values():
        for name in _segments_for_row(row):
            counts[name] += 1

    filtered = [row for row in rows.values() if _row_in_segment(row, segment)]
    filtered.sort(
        key=lambda row: (row["is_supporter"], row["monthly_amount"], _lifetime_spend(row)),
        reverse=True,
    )

    return Response({
        "segment": segment,
        "counts": counts,
        "count": len(filtered),
        "results": [_serialize_row(row) for row in filtered[:FAN_LIST_LIMIT]],
    })


def _broadcast_recipient_ids(artist, segment):
    rows = build_fan_rows(artist)
    return [fan_id for fan_id, row in rows.items() if _row_in_segment(row, segment)]


@api_view(["POST"])
def fan_broadcast(request):
    blocked = _artist_guard(request)
    if blocked:
        return blocked

    title = (request.data.get("title") or "").strip()
    body = (request.data.get("body") or "").strip()
    segment = request.data.get("segment") or "all"
    target_url = (request.data.get("target_url") or f"/?artist={request.user.username}").strip()

    if not title:
        return Response({"error": "A message title is required"}, status=status.HTTP_400_BAD_REQUEST)
    if not body:
        return Response({"error": "A message body is required"}, status=status.HTTP_400_BAD_REQUEST)
    if len(body) > 1000:
        return Response({"error": "Keep the message under 1000 characters"}, status=status.HTTP_400_BAD_REQUEST)
    if segment not in BROADCAST_SEGMENTS:
        return Response({"error": "Unknown segment"}, status=status.HTTP_400_BAD_REQUEST)

    cooldown_start = timezone.now() - timedelta(hours=BROADCAST_COOLDOWN_HOURS)
    recent = (
        Notification.objects
        .filter(actor=request.user, notification_type=Notification.MESSAGE, created_at__gte=cooldown_start)
        .order_by("-created_at")
        .first()
    )
    if recent:
        next_allowed = recent.created_at + timedelta(hours=BROADCAST_COOLDOWN_HOURS)
        return Response({
            "error": "You already messaged your fans in the last 24 hours.",
            "next_allowed_at": next_allowed,
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)

    from accounts.models import User

    recipient_ids = _broadcast_recipient_ids(request.user, segment)
    sent = 0
    for fan in User.objects.filter(id__in=recipient_ids, is_active=True):
        _create_notification(
            recipient=fan,
            actor=request.user,
            notification_type=Notification.MESSAGE,
            title=title[:180],
            body=body,
            target_url=target_url[:255],
        )
        sent += 1

    return Response({"sent": sent, "segment": segment}, status=status.HTTP_201_CREATED)
