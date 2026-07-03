import csv
from decimal import Decimal
from django.http import HttpResponse
from django.db.models import Count, Min, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .contact_utils import revoke_artist_fan_contact, sync_artist_fan_contact
from .journey import log_fan_journey_event
from .models import ArtistFanContact, ArtistFollow, ArtistProfessionProfile, ArtistProfile, FanJourneyEvent
from .business_health import get_artist_business_health
from artists.pro_insights import build_pro_insights
from .fans_also_support import get_fans_also_support
from .social_reach import sync_youtube_reach
from .trust import get_artist_trust_status
from artists.themes import normalize_artist_theme
from config.upload_validation import validate_image_upload, validate_video_upload
from posts.models import Post


def normalize_professions(data):
    raw_values = []
    valid_keys = ArtistProfile.valid_profession_keys()

    if hasattr(data, "getlist"):
        raw_values.extend(data.getlist("professions"))
        raw_values.extend(data.getlist("professions[]"))

    raw = data.get("professions", "")
    if isinstance(raw, list):
        raw_values.extend(raw)
    elif raw:
        raw_values.extend(str(raw).split(","))

    professions = []
    for value in raw_values:
        key = str(value).strip()
        if key in valid_keys and key not in professions:
            professions.append(key)

    return professions or [ArtistProfile.DEFAULT_PROFESSION]


def serialize_professions(artist):
    return [
        {"key": profession, "label": ArtistProfile.profession_label(profession)}
        for profession in artist.profession_list()
    ]


def serialize_profession_profiles(artist, request):
    profiles = {
        profile.profession: profile
        for profile in artist.profession_profiles.all()
    }
    data = {}

    for profession in artist.profession_list():
        profile = profiles.get(profession)
        data[profession] = {
            "profession": profession,
            "label": ArtistProfile.profession_label(profession),
            "display_title": profile.display_title if profile else "",
            "tagline": profile.tagline if profile else "",
            "bio": profile.bio if profile else "",
            "style": profile.style if profile else "",
            "cover_image": request.build_absolute_uri(profile.cover_image.url) if profile and profile.cover_image else None,
            "visitor_banner": request.build_absolute_uri(profile.visitor_banner.url) if profile and profile.visitor_banner else None,
            "visitor_banner_duration_seconds": profile.visitor_banner_duration_seconds if profile else 30,
        }

    return data


def serialize_artist_identity(artist_user, profession, request):
    from posts.models import Instant, PointOfView
    from posts.views import can_view_instant, serialize_instant, serialize_pov

    pov_filter = {
        "artist": artist_user,
        "is_pinned": True,
    }
    if profession:
        pov_filter["profession__in"] = ["", profession]

    pinned_pov = PointOfView.objects.select_related("artist").filter(**pov_filter).order_by("-created_at").first()
    active_instants = [
        instant
        for instant in Instant.objects.select_related("artist").filter(
            artist=artist_user,
            expires_at__gt=timezone.now(),
        ).order_by("-created_at")[:20]
        if can_view_instant(request.user, instant)
    ]

    return {
        "pinned_pov": serialize_pov(pinned_pov) if pinned_pov else None,
        "active_instants": [serialize_instant(instant, request) for instant in active_instants],
    }


def serialize_artist_upcoming(artist_user, profession, request):
    from artistcalendar.models import ArtistCalendarItem
    from artistcalendar.views import can_view_calendar_item, serialize_calendar_item

    items = ArtistCalendarItem.objects.select_related("artist").filter(
        artist=artist_user,
        profession=profession,
        starts_at__gte=timezone.now() - timezone.timedelta(days=1),
    ).order_by("starts_at")[:20]

    visible_items = [
        item for item in items
        if can_view_calendar_item(request.user, item)
    ]
    return [serialize_calendar_item(item, request) for item in visible_items[:6]]

@api_view(["GET"])
def artist_list(request):
    artists = ArtistProfile.objects.select_related("owner").prefetch_related("profession_profiles").order_by("-created_at")

    data = []
    for artist in artists:
        business_health = get_artist_business_health(artist.owner, artist)
        identity = serialize_artist_identity(artist.owner, artist.profession_list()[0], request)
        upcoming = serialize_artist_upcoming(artist.owner, artist.profession_list()[0], request)
        data.append({
            "id": artist.id,
            "stage_name": artist.stage_name,
            "genre": artist.genre,
            "city": artist.city,
            "artist_story": artist.artist_story,
            "influences": artist.influences,
            "instagram_url": artist.instagram_url,
            "tiktok_url": artist.tiktok_url,
            "youtube_url": artist.youtube_url,
            "website_url": artist.website_url,
            "youtube_reach": artist.youtube_reach_display(),
            "youtube_reach_verified": artist.youtube_reach_verified(),
            "youtube_reach_pending": artist.youtube_reach_pending(),
            "youtube_reach_synced_at": artist.youtube_reach_synced_at,
            "website_label": artist.website_label,
            "is_verified": artist.is_verified,
            "on_hiatus": artist.on_hiatus,
            "business_health": business_health,
            "pinned_pov": identity["pinned_pov"],
            "active_instants": identity["active_instants"],
            "upcoming_calendar_items": upcoming,
            "professions": serialize_professions(artist),
            "profession_keys": artist.profession_list(),
            "profession_profiles": serialize_profession_profiles(artist, request),
            "owner_id": artist.owner.id,
            "owner_username": artist.owner.username,
            "hero_image": request.build_absolute_uri(artist.hero_image.url) if artist.hero_image else None,
            "avatar": request.build_absolute_uri(artist.owner.avatar.url) if artist.owner.avatar else None,

            "show_music": artist.show_music,
            "show_posts": artist.show_posts,
            "show_store": artist.show_store,
            "show_lives": artist.show_lives,
            "show_about": artist.show_about,
            "theme_name": artist.theme_name,
            "studio_theme_name": artist.studio_theme_name,
        })

    return Response(data)


from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth import get_user_model
User = get_user_model()


def request_bool(data, field, default=False):
    value = data.get(field, default)
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def mask_email(email):
    if not email or "@" not in email:
        return ""
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[:2]}***@{domain}"


def serialize_mailing_contact(contact):
    from subscriptions.models import FanSubscription

    active_sub = (
        FanSubscription.objects
        .select_related("tier")
        .filter(fan=contact.fan, artist=contact.artist, active=True)
        .order_by("-started_at")
        .first()
    )
    return {
        "id": contact.id,
        "fan_id": contact.fan_id,
        "fan_username": contact.fan.username,
        "email": contact.fan.email,
        "masked_email": mask_email(contact.fan.email),
        "support_tier": active_sub.tier.name if active_sub and active_sub.tier else ("Supporter" if active_sub else ""),
        "location": contact.fan.discovery_location,
        "date_added": contact.shared_at,
        "active_subscription": bool(active_sub),
        "source": contact.source,
    }


def decimal_string(value):
    return str((value or Decimal("0.00")).quantize(Decimal("0.01")))


def serialize_money(amount, artist_share=None, platform_fee=None):
    amount = amount or Decimal("0.00")
    return {
        "amount": decimal_string(amount),
        "artist_share": decimal_string(artist_share if artist_share is not None else amount),
        "platform_fee": decimal_string(platform_fee),
    }

@api_view(["POST"])
def follow_artist(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    artist_id = request.data.get("artist_id")

    try:
        artist = User.objects.get(id=artist_id)
    except User.DoesNotExist:
        return Response({"error": "Artist not found"}, status=status.HTTP_404_NOT_FOUND)

    if artist.user_type != User.ARTIST or not ArtistProfile.objects.filter(owner=artist).exists():
        return Response({"error": "Artist profile not found"}, status=status.HTTP_400_BAD_REQUEST)

    if request.user == artist:
        return Response({"error": "You cannot follow yourself"}, status=status.HTTP_400_BAD_REQUEST)

    _, created = ArtistFollow.objects.get_or_create(
        fan=request.user,
        artist=artist
    )
    if created:
        log_fan_journey_event(
            FanJourneyEvent.FOLLOW,
            artist,
            fan=request.user,
            metadata={"referral_source": request.data.get("referral_source") or request.query_params.get("ref") or ""},
        )

    return Response({"message": "Following"})


@api_view(["POST"])
def unfollow_artist(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    artist_id = request.data.get("artist_id")

    ArtistFollow.objects.filter(
        fan=request.user,
        artist_id=artist_id
    ).delete()
    artist = User.objects.filter(id=artist_id, user_type=User.ARTIST).first()
    if artist:
        revoke_artist_fan_contact(request.user, artist)
        log_fan_journey_event(FanJourneyEvent.UNSUBSCRIBE, artist, fan=request.user, metadata={"source": "unfollow"})

    return Response({"message": "Unfollowed"})


@api_view(["GET"])
def mailing_list(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    contacts = (
        ArtistFanContact.objects
        .select_related("fan", "artist")
        .filter(artist=request.user, email_shared=True, fan__email__gt="")
        .order_by("-shared_at")
    )
    this_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = [serialize_mailing_contact(contact) for contact in contacts]
    can_export = request.user.artist_plan in {"pro", "studio"}

    if request.query_params.get("export") == "csv":
        if not can_export:
            return Response({"error": "Artist Pro is required for mailing list CSV export."}, status=status.HTTP_403_FORBIDDEN)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="indiefund-mailing-list.csv"'
        writer = csv.writer(response)
        writer.writerow(["email", "fan_username", "support_tier", "location", "date_added", "active_subscription", "source"])
        for row in rows:
            writer.writerow([
                row["email"],
                row["fan_username"],
                row["support_tier"],
                row["location"],
                row["date_added"],
                row["active_subscription"],
                row["source"],
            ])
        return response

    return Response({
        "count": len(rows),
        "added_this_month": contacts.filter(shared_at__gte=this_month).count(),
        "can_export": can_export,
        "results": rows,
    })


def _serialize_dashboard_spaces(artist):
    from spaces.models import SpaceBooking
    from spaces.local_draw import local_supporter_counts, resolve_local_city

    profile = getattr(artist, "artist_profile", None)
    city = resolve_local_city(profile.city if profile else "")
    local = local_supporter_counts(artist, city)
    upcoming_qs = SpaceBooking.objects.select_related("listing").filter(
        artist=artist,
        status=SpaceBooking.CONFIRMED,
        starts_at__gte=timezone.now(),
    )
    upcoming = upcoming_qs.order_by("starts_at")[:5]

    return {
        "city": city,
        "local_supporters": local["local_supporters"],
        "notifyable_local_supporters": local["notifyable_local_supporters_count"],
        "message": (
            f"{local['local_supporters']} local supporter(s) in {city}."
            if city
            else "Add your city to unlock local gig insights."
        ),
        "upcoming_gigs": upcoming_qs.count(),
        "upcoming_bookings": [
            {
                "id": booking.id,
                "venue_name": booking.listing.name,
                "city": booking.listing.city,
                "starts_at": booking.starts_at,
                "expected_audience": booking.expected_audience,
                "ticket_product_id": booking.ticket_product_id,
            }
            for booking in upcoming
        ],
    }


@api_view(["GET"])
def artist_dashboard(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    from marketplace.models import Product
    from mediahub.models import MusicUpload
    from subscriptions.models import FanSubscription, OneTimeTip

    now = timezone.now()
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_7d = now - timezone.timedelta(days=7)
    start_30d = now - timezone.timedelta(days=30)

    active_subscriptions = FanSubscription.objects.select_related("fan", "tier").filter(
        artist=request.user,
        active=True,
    )
    tips_this_month = OneTimeTip.objects.select_related("fan").filter(
        artist=request.user,
        created_at__gte=start_month,
    )
    tips_all = OneTimeTip.objects.filter(artist=request.user)

    mrr_amount = active_subscriptions.aggregate(total=Sum("monthly_amount"))["total"] or Decimal("0.00")
    mrr_artist_share = active_subscriptions.aggregate(total=Sum("artist_share"))["total"] or Decimal("0.00")
    mrr_platform_fee = active_subscriptions.aggregate(total=Sum("platform_fee"))["total"] or Decimal("0.00")
    tips_amount = tips_this_month.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    tips_artist_share = tips_this_month.aggregate(total=Sum("artist_share"))["total"] or Decimal("0.00")
    tips_platform_fee = tips_this_month.aggregate(total=Sum("platform_fee"))["total"] or Decimal("0.00")

    total_followers = ArtistFollow.objects.filter(artist=request.user).count()
    active_subscriber_ids = set(active_subscriptions.values_list("fan_id", flat=True))
    active_subscribers = len(active_subscriber_ids)
    new_subscribers_7d = active_subscriptions.filter(started_at__gte=start_7d).values("fan_id").distinct().count()
    new_subscribers_30d = active_subscriptions.filter(started_at__gte=start_30d).values("fan_id").distinct().count()
    mailing_contacts = ArtistFanContact.objects.filter(
        artist=request.user,
        email_shared=True,
        fan__email__gt="",
    )
    mailing_list_size = mailing_contacts.count()
    mailing_list_growth_30d = mailing_contacts.filter(shared_at__gte=start_30d).count()
    supporter_to_follower_ratio = (active_subscribers / total_followers * 100) if total_followers else 0

    subscription_spend = {}
    subscription_tenure = {}
    for row in active_subscriptions.values("fan_id", "fan__username", "fan__email").annotate(
        total=Sum("monthly_amount"),
        first_seen=Min("started_at"),
    ):
        subscription_spend[row["fan_id"]] = {
            "fan_id": row["fan_id"],
            "fan_username": row["fan__username"],
            "fan_email": row["fan__email"],
            "subscription_total": row["total"] or Decimal("0.00"),
            "tip_total": Decimal("0.00"),
            "purchase_total": Decimal("0.00"),
            "first_seen": row["first_seen"],
        }
        subscription_tenure[row["fan_id"]] = row["first_seen"]

    for row in tips_all.values("fan_id", "fan__username", "fan__email").annotate(
        total=Sum("amount"),
        first_seen=Min("created_at"),
    ):
        supporter = subscription_spend.setdefault(row["fan_id"], {
            "fan_id": row["fan_id"],
            "fan_username": row["fan__username"],
            "fan_email": row["fan__email"],
            "subscription_total": Decimal("0.00"),
            "tip_total": Decimal("0.00"),
            "purchase_total": Decimal("0.00"),
            "first_seen": row["first_seen"],
        })
        supporter["tip_total"] = row["total"] or Decimal("0.00")
        if not supporter["first_seen"] or row["first_seen"] < supporter["first_seen"]:
            supporter["first_seen"] = row["first_seen"]

    top_supporters = []
    for supporter in subscription_spend.values():
        total_spend = supporter["subscription_total"] + supporter["tip_total"] + supporter["purchase_total"]
        first_seen = supporter["first_seen"]
        tenure_days = (now - first_seen).days if first_seen else 0
        top_supporters.append({
            "fan_id": supporter["fan_id"],
            "fan_username": supporter["fan_username"],
            "fan_email": supporter["fan_email"],
            "total_spend": decimal_string(total_spend),
            "subscription_total": decimal_string(supporter["subscription_total"]),
            "tips_total": decimal_string(supporter["tip_total"]),
            "purchase_total": decimal_string(supporter["purchase_total"]),
            "tenure_days": tenure_days,
            "first_seen": first_seen,
        })
    top_supporters.sort(key=lambda item: Decimal(item["total_spend"]), reverse=True)

    recent_follows = ArtistFollow.objects.select_related("fan").filter(
        artist=request.user,
        created_at__gte=start_7d,
    ).order_by("-created_at")[:10]
    recent_subscriptions = FanSubscription.objects.select_related("fan", "tier").filter(
        artist=request.user,
        started_at__gte=start_7d,
    ).order_by("-started_at")[:10]
    recent_activity = [
        {
            "id": f"follow-{item.id}",
            "type": "follow",
            "title": f"{item.fan.username} followed you",
            "detail": "New fan relationship captured.",
            "created_at": item.created_at,
        }
        for item in recent_follows
    ] + [
        {
            "id": f"subscription-{item.id}",
            "type": "subscription",
            "title": f"{item.fan.username} became a supporter",
            "detail": f"${item.monthly_amount}/month{f' via {item.tier.name}' if item.tier else ''}",
            "created_at": item.started_at,
        }
        for item in recent_subscriptions
    ]
    recent_activity.sort(key=lambda item: item["created_at"], reverse=True)

    product_count = Product.objects.filter(artist=request.user, is_active=True).count()
    event_counts = {
        row["event_type"]: row["count"]
        for row in FanJourneyEvent.objects.filter(artist=request.user).values("event_type").annotate(count=Count("id"))
    }
    visitors = FanJourneyEvent.objects.filter(
        artist=request.user,
        event_type=FanJourneyEvent.PAGE_VIEW,
    ).values("fan_id").distinct().count()
    repeat_purchasers = FanJourneyEvent.objects.filter(
        artist=request.user,
        event_type=FanJourneyEvent.PURCHASE,
    ).values("fan_id").annotate(count=Count("id")).filter(count__gte=2).count()
    referral_rows = (
        FanJourneyEvent.objects
        .filter(
            artist=request.user,
            event_type=FanJourneyEvent.SUBSCRIBE,
            occurred_at__gte=start_month,
        )
        .exclude(metadata__referral_source__in=["", None])
        .values("metadata__referral_source")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    referrals_this_month = [
        {
            "source": row["metadata__referral_source"],
            "supporters": row["count"],
        }
        for row in referral_rows
    ]

    from posts.models import Like
    from django.db.models import Count as DbCount

    audience_city_rows = (
        User.objects.filter(
            id__in=FanSubscription.objects.filter(artist=request.user, active=True).values("fan_id")
        )
        .exclude(discovery_location="")
        .values("discovery_location")
        .annotate(count=DbCount("id"))
        .order_by("-count")[:8]
    )
    audience_cities = [
        {"city": row["discovery_location"], "count": row["count"]}
        for row in audience_city_rows
    ]

    engaging_posts = []
    for post in Post.objects.filter(author=request.user, is_hidden=False).annotate(
        like_count=DbCount("likes"),
        comment_count=DbCount("comments"),
    ).order_by("-like_count", "-created_at")[:5]:
        engaging_posts.append({
            "type": "post",
            "id": post.id,
            "title": post.title or post.body[:80],
            "likes": post.like_count,
            "comments": post.comment_count,
        })

    churn_30d = FanJourneyEvent.objects.filter(
        artist=request.user,
        event_type=FanJourneyEvent.UNSUBSCRIBE,
        occurred_at__gte=start_30d,
    ).count()
    invite_follows = FanJourneyEvent.objects.filter(
        artist=request.user,
        event_type=FanJourneyEvent.FOLLOW,
    ).exclude(metadata__referral_source__in=["", None]).count()
    invite_subscribers = FanJourneyEvent.objects.filter(
        artist=request.user,
        event_type=FanJourneyEvent.SUBSCRIBE,
    ).exclude(metadata__referral_source__in=["", None]).count()

    track_metrics = []
    for track in MusicUpload.objects.filter(artist=request.user).order_by("-created_at"):
        preview_events = FanJourneyEvent.objects.filter(
            artist=request.user,
            music_upload=track,
            event_type=FanJourneyEvent.MUSIC_PREVIEW,
        )
        full_play_events = FanJourneyEvent.objects.filter(
            artist=request.user,
            music_upload=track,
            event_type=FanJourneyEvent.MUSIC_FULL_PLAY,
        )
        converted_fan_ids = set()
        first_listens = {}
        for event in FanJourneyEvent.objects.filter(
            artist=request.user,
            music_upload=track,
            event_type__in=[FanJourneyEvent.MUSIC_PREVIEW, FanJourneyEvent.MUSIC_FULL_PLAY],
            fan__isnull=False,
        ).order_by("fan_id", "occurred_at"):
            first_listens.setdefault(event.fan_id, event.occurred_at)
        for fan_id, first_listen_at in first_listens.items():
            if FanJourneyEvent.objects.filter(
                artist=request.user,
                fan_id=fan_id,
                event_type=FanJourneyEvent.SUBSCRIBE,
                occurred_at__gte=first_listen_at,
                occurred_at__lte=first_listen_at + timezone.timedelta(days=7),
            ).exists():
                converted_fan_ids.add(fan_id)
        track_metrics.append({
            "track_id": track.id,
            "title": track.title,
            "preview_plays": preview_events.count(),
            "full_plays": full_play_events.count(),
            "subscriber_conversions_7d": len(converted_fan_ids),
        })

    marketplace_purchases = FanJourneyEvent.objects.filter(
        artist=request.user,
        event_type=FanJourneyEvent.PURCHASE,
        occurred_at__gte=start_month,
    )
    marketplace_amount = Decimal("0.00")
    marketplace_artist_share = Decimal("0.00")
    marketplace_platform_fee = Decimal("0.00")
    for event in marketplace_purchases:
        marketplace_amount += Decimal(str(event.metadata.get("amount", "0") or "0"))
        marketplace_artist_share += Decimal(str(event.metadata.get("artist_share", "0") or "0"))
        marketplace_platform_fee += Decimal(str(event.metadata.get("platform_fee", "0") or "0"))
    marketplace_sales = serialize_money(marketplace_amount, marketplace_artist_share, marketplace_platform_fee)
    marketplace_tracking_ready = True

    visitor_to_subscriber_rate = round((active_subscribers / visitors) * 100, 2) if visitors else 0
    follower_to_subscriber_rate = round(supporter_to_follower_ratio, 2)

    total_revenue_amount = mrr_amount + tips_amount + marketplace_amount
    total_artist_share = mrr_artist_share + tips_artist_share + marketplace_artist_share
    total_platform_fee = mrr_platform_fee + tips_platform_fee + marketplace_platform_fee
    trust_status = get_artist_trust_status(request.user)

    from config.platform_fees import fee_schedule
    from .connect import fetch_connect_status

    return Response({
        "fee_schedule": fee_schedule(),
        "payouts": fetch_connect_status(request.user.artist_profile),
        "revenue": {
            "mrr": serialize_money(mrr_amount, mrr_artist_share, mrr_platform_fee),
            "tips_this_month": serialize_money(tips_amount, tips_artist_share, tips_platform_fee),
            "marketplace_sales_this_month": marketplace_sales,
            "marketplace_tracking_ready": marketplace_tracking_ready,
            "total_revenue_this_month": serialize_money(total_revenue_amount, total_artist_share, total_platform_fee),
            "platform_fees_this_month": decimal_string(total_platform_fee),
            "artist_share_this_month": decimal_string(total_artist_share),
        },
        "fans": {
            "total_followers": total_followers,
            "active_subscribers": active_subscribers,
            "new_subscribers_7d": new_subscribers_7d,
            "new_subscribers_30d": new_subscribers_30d,
            "mailing_list_size": mailing_list_size,
            "mailing_list_growth_30d": mailing_list_growth_30d,
        },
        "ratios": {
            "supporter_to_follower_ratio": round(supporter_to_follower_ratio, 2),
            "visitor_to_subscriber_rate": visitor_to_subscriber_rate,
            "follower_to_subscriber_rate": follower_to_subscriber_rate,
        },
        "funnel": {
            "visitors": visitors,
            "followers": total_followers,
            "subscribers": active_subscribers,
            "repeat_purchasers": repeat_purchasers,
            "event_counts": event_counts,
        },
        "referrals": {
            "supporters_this_month": referrals_this_month,
            "invite_follows": invite_follows,
            "invite_subscribers": invite_subscribers,
        },
        "audience_cities": audience_cities,
        "engaging_content": engaging_posts,
        "retention": {
            "churn_30d": churn_30d,
            "repeat_purchasers": repeat_purchasers,
            "new_subscribers_30d": new_subscribers_30d,
        },
        "music_funnel": {
            "tracks": track_metrics,
        },
        "top_supporters": top_supporters[:10],
        "recent_activity": recent_activity[:20],
        "setup": {
            "product_count": product_count,
            "support_tier_count": request.user.support_tiers.filter(is_active=True).count(),
            "public_page_url": f"/?artist={request.user.username}",
        },
        "spaces": _serialize_dashboard_spaces(request.user),
        "trust": {
            "profile_complete": trust_status["profile_completion"]["complete"],
            "bot_risk_level": trust_status["bot_risk"]["level"],
            "open_ai_review_flags": trust_status["open_ai_review_flags"],
            "upload_limit_message": trust_status["upload_limit_message"],
            "missing_profile_items": trust_status["profile_completion"]["missing"],
            "ai_review_flags": trust_status["ai_review_flags"],
        },
    })


@api_view(["GET", "POST"])
def fan_email_sharing(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == "POST":
        artist_id = request.data.get("artist_id")
        try:
            artist = User.objects.get(id=artist_id, user_type=User.ARTIST)
        except User.DoesNotExist:
            return Response({"error": "Artist not found"}, status=status.HTTP_404_NOT_FOUND)

        email_shared = request_bool(request.data, "email_shared", False)
        if email_shared:
            sync_artist_fan_contact(request.user, artist, source=ArtistFanContact.MANUAL, explicit_share=True)
        else:
            revoke_artist_fan_contact(request.user, artist)

    contacts = (
        ArtistFanContact.objects
        .select_related("artist", "artist__artist_profile")
        .filter(fan=request.user)
        .order_by("artist__username")
    )
    return Response({
        "results": [
            {
                "artist_id": contact.artist_id,
                "artist_username": contact.artist.username,
                "artist_name": getattr(getattr(contact.artist, "artist_profile", None), "stage_name", contact.artist.username),
                "email_shared": contact.email_shared,
                "shared_at": contact.shared_at,
                "revoked_at": contact.revoked_at,
                "source": contact.source,
            }
            for contact in contacts
        ],
        "count": contacts.count(),
    })


@api_view(["POST"])
def record_page_view(request):
    artist_id = request.data.get("artist_id")
    try:
        artist = User.objects.get(id=artist_id, user_type=User.ARTIST)
    except User.DoesNotExist:
        return Response({"error": "Artist not found"}, status=status.HTTP_404_NOT_FOUND)

    log_fan_journey_event(
        FanJourneyEvent.PAGE_VIEW,
        artist,
        fan=request.user if request.user.is_authenticated else None,
        metadata={"source": request.data.get("source") or "artist_page"},
    )

    return Response({"message": "Page view recorded."}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def fans_also_support(request):
    artist_id = request.query_params.get("artist_id")
    if not artist_id:
        return Response({"error": "artist_id is required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        artist = User.objects.get(id=artist_id, user_type=User.ARTIST)
    except User.DoesNotExist:
        return Response({"error": "Artist not found"}, status=status.HTTP_404_NOT_FOUND)

    limit = min(int(request.query_params.get("limit") or 5), 8)
    results = get_fans_also_support(artist, request, limit=limit)
    return Response({"results": results, "count": len(results)})


@api_view(["GET"])
def follow_stats(request):

    data = {}

    for user in User.objects.all():

        data[user.username] = {
            "followers": ArtistFollow.objects.filter(
                artist=user
            ).count(),

            "following": ArtistFollow.objects.filter(
                fan=user
            ).count()
        }

    return Response(data)


@api_view(["POST"])
def update_artist_profile(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    artist, _ = ArtistProfile.objects.get_or_create(
        owner=request.user,
        defaults={"stage_name": request.user.display_name or request.user.username},
    )

    artist.stage_name = request.data.get("stage_name", artist.stage_name)
    artist.genre = request.data.get("genre", artist.genre)
    artist.city = request.data.get("city", artist.city)
    artist.artist_story = request.data.get("artist_story", artist.artist_story)
    artist.influences = request.data.get("influences", artist.influences)
    artist.instagram_url = request.data.get("instagram_url", artist.instagram_url)
    artist.tiktok_url = request.data.get("tiktok_url", artist.tiktok_url)
    previous_youtube_url = artist.youtube_url
    artist.youtube_url = request.data.get("youtube_url", artist.youtube_url)
    artist.website_url = request.data.get("website_url", artist.website_url)
    artist.website_label = request.data.get("website_label", artist.website_label)
    artist.professions = ",".join(normalize_professions(request.data))
    artist.on_hiatus = request_bool(request.data, "on_hiatus", artist.on_hiatus)
    if request.FILES.get("hero_image"):
        artist.hero_image = request.FILES["hero_image"]

    artist.save()

    if artist.youtube_url != previous_youtube_url:
        sync_youtube_reach(artist)

    active_profession = request.data.get("active_profession")
    if active_profession in artist.profession_list():
        profession_profile, _ = ArtistProfessionProfile.objects.get_or_create(
            artist_profile=artist,
            profession=active_profession,
        )
        profession_profile.display_title = request.data.get("profession_display_title", profession_profile.display_title)
        profession_profile.tagline = request.data.get("profession_tagline", profession_profile.tagline)
        profession_profile.bio = request.data.get("profession_bio", profession_profile.bio)
        profession_profile.style = request.data.get("profession_style", profession_profile.style)
        if request.FILES.get("profession_cover_image"):
            cover_error = validate_image_upload(request.FILES["profession_cover_image"], "Cover photo")
            if cover_error:
                return Response({"error": cover_error}, status=status.HTTP_400_BAD_REQUEST)
            profession_profile.cover_image = request.FILES["profession_cover_image"]
        if request.FILES.get("profession_visitor_banner"):
            banner_error = validate_video_upload(request.FILES["profession_visitor_banner"], "Visitor banner")
            if banner_error:
                return Response({"error": banner_error}, status=status.HTTP_400_BAD_REQUEST)
            profession_profile.visitor_banner = request.FILES["profession_visitor_banner"]
        duration_raw = request.data.get("profession_visitor_banner_duration")
        if duration_raw not in {None, ""}:
            try:
                duration = int(duration_raw)
            except (TypeError, ValueError):
                duration = None
            if duration in ArtistProfessionProfile.VISITOR_BANNER_DURATIONS:
                profession_profile.visitor_banner_duration_seconds = duration
        if request_bool(request.data, "profession_clear_visitor_banner", False):
            if profession_profile.visitor_banner:
                profession_profile.visitor_banner.delete(save=False)
            profession_profile.visitor_banner = None
        profession_profile.save()

    return Response({
        "message": "Profile updated",
        "hero_image": request.build_absolute_uri(artist.hero_image.url) if artist.hero_image else None,
        "profession_profiles": serialize_profession_profiles(artist, request),
    })


@api_view(["POST"])
def update_page_builder(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    artist, _ = ArtistProfile.objects.get_or_create(
        owner=request.user,
        defaults={"stage_name": request.user.display_name or request.user.username},
    )

    artist.show_music = request_bool(request.data, "show_music", artist.show_music)
    artist.show_posts = request_bool(request.data, "show_posts", artist.show_posts)
    artist.show_store = request_bool(request.data, "show_store", artist.show_store)
    artist.show_lives = request_bool(request.data, "show_lives", artist.show_lives)
    artist.show_about = request_bool(request.data, "show_about", artist.show_about)
    if "theme_name" in request.data:
        artist.theme_name = normalize_artist_theme(request.data.get("theme_name"))
    if "studio_theme_name" in request.data:
        artist.studio_theme_name = normalize_artist_theme(request.data.get("studio_theme_name"))

    artist.save()

    return Response({
        "message": "Page layout updated",
        "theme_name": artist.theme_name,
        "studio_theme_name": artist.studio_theme_name,
    })


@api_view(["GET"])
def artist_trust_status(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)
    return Response(get_artist_trust_status(request.user))


@api_view(["GET"])
def artist_pro_insights(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)
    if request.user.artist_plan not in {"pro", "studio"}:
        return Response({"error": "Artist Pro or Studio is required for development insights."}, status=status.HTTP_403_FORBIDDEN)
    from .pro_insights import build_pro_insights
    return Response(build_pro_insights(request.user))


@api_view(["GET"])
def stripe_connect_status(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    from .connect import fetch_connect_status

    return Response(fetch_connect_status(request.user.artist_profile))


@api_view(["POST"])
def stripe_connect_onboarding(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    from django.conf import settings
    from .connect import connect_configured, create_connect_onboarding_link

    if settings.DEBUG and not connect_configured():
        profile = request.user.artist_profile
        if not profile.stripe_connect_account_id:
            profile.stripe_connect_account_id = f"acct_demo_{request.user.id}"
            profile.save(update_fields=["stripe_connect_account_id"])
        return Response({
            "onboarding_url": f"{settings.FRONTEND_URL}/?connect=demo",
            "demo_mode": True,
        })

    onboarding_url, error = create_connect_onboarding_link(request.user.artist_profile)
    if error:
        return Response({"error": error}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({"onboarding_url": onboarding_url})
