"""Platform-controlled social reach.

Follower/subscriber numbers are never typed by artists. They are fetched from
official platform APIs so the figures shown to fans are verifiable.

Currently only YouTube is supported, via the official YouTube Data API v3.
Other platforms (Instagram, TikTok) have no legitimate public endpoint for
follower counts, so they are intentionally not displayed.
"""

import json
import logging
import re
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/channels"
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
REQUEST_TIMEOUT_SECONDS = 6


def _youtube_api_key():
    return getattr(settings, "YOUTUBE_API_KEY", "") or ""


def parse_youtube_target(url):
    """Return a (param, value) tuple for the YouTube Data API channels lookup.

    Handles the common URL shapes:
      - https://youtube.com/channel/UCxxxx        -> ("id", "UCxxxx")
      - https://youtube.com/@handle               -> ("forHandle", "@handle")
      - https://youtube.com/user/legacyname       -> ("forUsername", "legacyname")
      - https://youtube.com/c/CustomName          -> ("search", "CustomName")
    """
    if not url:
        return None

    cleaned = url.strip()
    if not cleaned:
        return None

    if not re.match(r"^https?://", cleaned, re.IGNORECASE):
        cleaned = f"https://{cleaned}"

    parsed = urlparse(cleaned)
    host = (parsed.netloc or "").lower()
    if "youtube.com" not in host and "youtu.be" not in host:
        return None

    path = (parsed.path or "").strip("/")
    if not path:
        return None

    segments = [segment for segment in path.split("/") if segment]
    first = segments[0]

    if first.startswith("@"):
        return ("forHandle", first)
    if first == "channel" and len(segments) > 1:
        return ("id", segments[1])
    if first == "user" and len(segments) > 1:
        return ("forUsername", segments[1])
    if first == "c" and len(segments) > 1:
        return ("search", segments[1])
    return ("search", first)


def _http_get_json(url):
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _resolve_channel_id_via_search(query, api_key):
    url = (
        f"{YOUTUBE_SEARCH_URL}?part=snippet&type=channel&maxResults=1"
        f"&q={quote(query)}&key={api_key}"
    )
    payload = _http_get_json(url)
    items = payload.get("items") or []
    if not items:
        return None
    return items[0].get("snippet", {}).get("channelId") or items[0].get("id", {}).get("channelId")


def fetch_youtube_channel(url):
    """Return {"channel_id", "subscriber_count"} for a YouTube URL, or None.

    Returns None when there is no API key configured, the URL cannot be
    parsed, the channel hides its subscriber count, or the request fails.
    """
    api_key = _youtube_api_key()
    if not api_key:
        return None

    target = parse_youtube_target(url)
    if not target:
        return None

    param, value = target
    try:
        if param == "search":
            channel_id = _resolve_channel_id_via_search(value, api_key)
            if not channel_id:
                return None
            param, value = "id", channel_id

        lookup_url = (
            f"{YOUTUBE_API_URL}?part=statistics&{param}={quote(value)}&key={api_key}"
        )
        payload = _http_get_json(lookup_url)
        items = payload.get("items") or []
        if not items:
            return None

        item = items[0]
        statistics = item.get("statistics", {})
        if statistics.get("hiddenSubscriberCount"):
            return {"channel_id": item.get("id", ""), "subscriber_count": None}

        raw_count = statistics.get("subscriberCount")
        if raw_count is None:
            return {"channel_id": item.get("id", ""), "subscriber_count": None}

        return {
            "channel_id": item.get("id", ""),
            "subscriber_count": int(raw_count),
        }
    except Exception as error:  # network/parse errors must not break profile saves
        logger.warning("YouTube reach fetch failed for %s: %s", url, error)
        return None


def sync_youtube_reach(artist):
    """Best-effort refresh of an artist's verified YouTube reach.

    Safe to call inline on profile save: it never raises and clears stale
    counts if the URL was removed.
    """
    url = (artist.youtube_url or "").strip()
    if not url:
        if artist.youtube_subscriber_count is not None or artist.youtube_channel_id:
            artist.youtube_channel_id = ""
            artist.youtube_subscriber_count = None
            artist.youtube_reach_synced_at = None
            artist.save(update_fields=[
                "youtube_channel_id",
                "youtube_subscriber_count",
                "youtube_reach_synced_at",
            ])
        return None

    result = fetch_youtube_channel(url)
    if result is None:
        return None

    artist.youtube_channel_id = result.get("channel_id", "")
    artist.youtube_subscriber_count = result.get("subscriber_count")
    artist.youtube_reach_synced_at = timezone.now()
    artist.save(update_fields=[
        "youtube_channel_id",
        "youtube_subscriber_count",
        "youtube_reach_synced_at",
    ])
    return artist.youtube_subscriber_count
