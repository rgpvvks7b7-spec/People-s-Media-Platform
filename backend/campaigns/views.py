import json
from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .models import Campaign
from .providers import validate_campaign_for_networks
from .services import placeholder_metrics_for_campaign

MAX_IMAGE_SIZE = 8 * 1024 * 1024
MAX_VIDEO_SIZE = 50 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov"}
ALLOWED_CREATIVE_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS


def artist_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        if request.user.user_type != "artist":
            return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)
        return view_func(request, *args, **kwargs)

    return wrapper


def validate_creative_upload(file_obj):
    if not file_obj:
        return None

    name = file_obj.name.lower()
    if not any(name.endswith(ext) for ext in ALLOWED_CREATIVE_EXTENSIONS):
        return f"Creative file must be one of: {', '.join(sorted(ALLOWED_CREATIVE_EXTENSIONS))}"

    is_video = any(name.endswith(ext) for ext in ALLOWED_VIDEO_EXTENSIONS)
    max_size = MAX_VIDEO_SIZE if is_video else MAX_IMAGE_SIZE
    if file_obj.size > max_size:
        return "Creative file is too large."

    return None


def parse_decimal(value, default=None):
    if value in {None, ""}:
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def parse_int(value, default=None):
    if value in {None, ""}:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_json_list(value):
    if isinstance(value, list):
        return value
    if value is None or value == "":
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            return [item.strip() for item in value.split(",") if item.strip()]
    return []


def normalize_ad_networks(value):
    networks = []
    for item in parse_json_list(value):
        key = str(item).strip().lower()
        if key in Campaign.VALID_AD_NETWORKS and key not in networks:
            networks.append(key)
    return networks


def normalize_string_list(value):
    items = []
    for item in parse_json_list(value):
        text = str(item).strip()
        if text and text not in items:
            items.append(text)
    return items


def request_data(request):
    if hasattr(request, "data") and request.data:
        return request.data
    return request.POST


def serialize_metrics(campaign):
    data = placeholder_metrics_for_campaign(campaign)
    return {
        "impressions": data["impressions"],
        "clicks": data["clicks"],
        "follows": data["follows"],
        "subscribers": data["subscribers"],
        "purchases": data["purchases"],
        "revenue": str(data["revenue"]),
        "fan_value": str(data["fan_value"]),
        "placeholder": data["placeholder"],
    }


def serialize_campaign(campaign, request):
    creative_url = ""
    if campaign.creative_file:
        creative_url = request.build_absolute_uri(campaign.creative_file.url)

    return {
        "id": campaign.id,
        "title": campaign.title,
        "campaign_type": campaign.campaign_type,
        "goal": campaign.goal,
        "ad_networks": campaign.ad_networks or [],
        "destination_type": campaign.destination_type,
        "destination_url": campaign.destination_url,
        "budget_daily": str(campaign.budget_daily),
        "budget_total": str(campaign.budget_total),
        "duration_days": campaign.duration_days,
        "audience_description": campaign.audience_description,
        "similar_artists": campaign.similar_artists or [],
        "locations": campaign.locations or [],
        "age_min": campaign.age_min,
        "age_max": campaign.age_max,
        "creative_headline": campaign.creative_headline,
        "creative_text": campaign.creative_text,
        "creative_file_url": creative_url,
        "status": campaign.status,
        "created_at": campaign.created_at.isoformat(),
        "updated_at": campaign.updated_at.isoformat(),
        "metrics": serialize_metrics(campaign),
    }


def apply_campaign_fields(campaign, data, request, *, partial=False):
    errors = []

    def should_set(field):
        return not partial or field in data

    if should_set("title"):
        title = (data.get("title") or "").strip()
        if not title:
            errors.append("title is required.")
        else:
            campaign.title = title[:180]

    if should_set("campaign_type"):
        campaign_type = (data.get("campaign_type") or "").strip()
        valid_types = {choice[0] for choice in Campaign.CAMPAIGN_TYPES}
        if campaign_type and campaign_type not in valid_types:
            errors.append("Invalid campaign_type.")
        elif campaign_type:
            campaign.campaign_type = campaign_type

    if should_set("goal"):
        goal = (data.get("goal") or "").strip()
        valid_goals = {choice[0] for choice in Campaign.GOALS}
        if goal and goal not in valid_goals:
            errors.append("Invalid goal.")
        elif goal:
            campaign.goal = goal

    if should_set("ad_networks"):
        campaign.ad_networks = normalize_ad_networks(data.get("ad_networks"))

    if should_set("destination_type"):
        destination_type = (data.get("destination_type") or "").strip()
        valid_destinations = {choice[0] for choice in Campaign.DESTINATION_TYPES}
        if destination_type and destination_type not in valid_destinations:
            errors.append("Invalid destination_type.")
        elif destination_type:
            campaign.destination_type = destination_type

    if should_set("destination_url"):
        campaign.destination_url = (data.get("destination_url") or "").strip()[:500]

    if should_set("budget_daily"):
        budget_daily = parse_decimal(data.get("budget_daily"))
        if budget_daily is not None and budget_daily >= 0:
            campaign.budget_daily = budget_daily

    if should_set("budget_total"):
        budget_total = parse_decimal(data.get("budget_total"))
        if budget_total is not None and budget_total >= 0:
            campaign.budget_total = budget_total

    if should_set("duration_days"):
        duration_days = parse_int(data.get("duration_days"))
        if duration_days is not None and duration_days > 0:
            campaign.duration_days = duration_days

    if should_set("audience_description"):
        campaign.audience_description = (data.get("audience_description") or "").strip()

    if should_set("similar_artists"):
        campaign.similar_artists = normalize_string_list(data.get("similar_artists"))

    if should_set("locations"):
        campaign.locations = normalize_string_list(data.get("locations"))

    if should_set("age_min"):
        campaign.age_min = parse_int(data.get("age_min"))

    if should_set("age_max"):
        campaign.age_max = parse_int(data.get("age_max"))

    if should_set("creative_headline"):
        campaign.creative_headline = (data.get("creative_headline") or "").strip()[:200]

    if should_set("creative_text"):
        campaign.creative_text = (data.get("creative_text") or "").strip()

    if should_set("status"):
        status_value = (data.get("status") or "").strip()
        valid_statuses = {choice[0] for choice in Campaign.STATUSES}
        if status_value and status_value not in valid_statuses:
            errors.append("Invalid status.")
        elif status_value:
            campaign.status = status_value

    if "creative_file" in request.FILES:
        upload_error = validate_creative_upload(request.FILES["creative_file"])
        if upload_error:
            errors.append(upload_error)
        else:
            campaign.creative_file = request.FILES["creative_file"]

    return errors


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
@artist_required
def campaign_list_create(request):
    if request.method == "GET":
        campaigns = Campaign.objects.filter(artist=request.user)
        return Response({
            "results": [serialize_campaign(item, request) for item in campaigns],
        })

    data = request_data(request)
    campaign = Campaign(artist=request.user)
    errors = apply_campaign_fields(campaign, data, request, partial=False)
    if errors:
        return Response({"error": " ".join(errors)}, status=status.HTTP_400_BAD_REQUEST)

    if not campaign.title:
        return Response({"error": "title is required."}, status=status.HTTP_400_BAD_REQUEST)

    if campaign.status == Campaign.READY:
        validation_errors = validate_campaign_for_networks(campaign)
        if validation_errors:
            return Response({"error": " ".join(validation_errors)}, status=status.HTTP_400_BAD_REQUEST)

    campaign.save()
    return Response({
        "message": "Campaign saved.",
        "campaign": serialize_campaign(campaign, request),
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@artist_required
def campaign_detail(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id, artist=request.user)
    return Response({"campaign": serialize_campaign(campaign, request)})


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
@artist_required
def campaign_update(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id, artist=request.user)
    data = request_data(request)
    errors = apply_campaign_fields(campaign, data, request, partial=True)
    if errors:
        return Response({"error": " ".join(errors)}, status=status.HTTP_400_BAD_REQUEST)

    if campaign.status == Campaign.READY:
        validation_errors = validate_campaign_for_networks(campaign)
        if validation_errors:
            return Response({"error": " ".join(validation_errors)}, status=status.HTTP_400_BAD_REQUEST)

    campaign.save()
    return Response({
        "message": "Campaign updated.",
        "campaign": serialize_campaign(campaign, request),
    })


@api_view(["POST"])
@artist_required
def campaign_delete(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id, artist=request.user)
    campaign.delete()
    return Response({"message": "Campaign deleted."})
