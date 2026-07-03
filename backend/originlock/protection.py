"""Protected media foundation: access logging, abuse heuristics, and labels.

Honesty notes:
- None of this makes AI analysis of audible audio impossible. If a human can
  hear or record a stream, a machine can too. The goal is to make scraping and
  mass-downloading hard, auditable, and clearly unauthorised.
- No biometric data is stored. Acoustic fingerprints (future) identify the
  recording, never a person.
- This is not DRM. Files are served behind signed, expiring tokens and every
  access is logged.
"""

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import MediaAbuseFlag, MediaAccessLog

# Public warning copy rendered on product/track pages.
PROTECTED_WORK_NOTICE = (
    "This work is protected. Uploading, scraping, cloning, training AI models, "
    "or redistributing without permission is prohibited."
)

ABUSE_WINDOW_MINUTES = 10
MAX_STREAMS_PER_WINDOW = 60
MAX_DOWNLOADS_PER_WINDOW = 10
MAX_FULL_ACCESS_PER_OBJECT_PER_WINDOW = 10

BOT_USER_AGENT_MARKERS = (
    "bot",
    "crawl",
    "spider",
    "scrapy",
    "curl",
    "wget",
    "python-requests",
    "httpclient",
    "headless",
)


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def compute_acoustic_fingerprint(file_obj):
    """Placeholder for perceptual audio fingerprinting (e.g. chromaprint).

    Returns an empty string until a real fingerprinting pipeline exists.
    Intentionally never derives anything from a person - only the recording.
    """
    return ""


def log_media_access(request, content_object, artist, access_type):
    """Record a protected-file access and run scraping heuristics.

    Logging must never break media delivery, so failures are swallowed.
    """
    try:
        content_type = ContentType.objects.get_for_model(type(content_object))
        log = MediaAccessLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            artist=artist,
            content_type=content_type,
            object_id=content_object.pk,
            access_type=access_type,
            ip_address=client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:400],
        )
        _detect_abuse(log)
        return log
    except Exception:
        return None


def _recent_logs(log):
    window_start = timezone.now() - timezone.timedelta(minutes=ABUSE_WINDOW_MINUTES)
    queryset = MediaAccessLog.objects.filter(created_at__gte=window_start)
    if log.user_id:
        return queryset.filter(user_id=log.user_id)
    return queryset.filter(user__isnull=True, ip_address=log.ip_address)


def _raise_flag(log, flag_type, detail):
    window_start = timezone.now() - timezone.timedelta(minutes=ABUSE_WINDOW_MINUTES)
    existing = MediaAbuseFlag.objects.filter(
        flag_type=flag_type,
        status=MediaAbuseFlag.OPEN,
        created_at__gte=window_start,
    )
    if log.user_id:
        existing = existing.filter(user_id=log.user_id)
    else:
        existing = existing.filter(user__isnull=True, ip_address=log.ip_address)
    if existing.exists():
        return None

    return MediaAbuseFlag.objects.create(
        flag_type=flag_type,
        user_id=log.user_id,
        artist_id=log.artist_id,
        content_type_id=log.content_type_id,
        object_id=log.object_id,
        ip_address=log.ip_address,
        detail=detail[:300],
    )


def _detect_abuse(log):
    agent = (log.user_agent or "").lower()
    if not agent or any(marker in agent for marker in BOT_USER_AGENT_MARKERS):
        _raise_flag(
            log,
            MediaAbuseFlag.BOT_LIKE_ACCESS,
            f"Suspicious user agent: {log.user_agent or '(empty)'}",
        )

    recent = _recent_logs(log)

    stream_count = recent.filter(
        access_type__in=[MediaAccessLog.STREAM, MediaAccessLog.PREVIEW],
    ).count()
    if stream_count > MAX_STREAMS_PER_WINDOW:
        _raise_flag(
            log,
            MediaAbuseFlag.TOO_MANY_STREAMS,
            f"{stream_count} streams in {ABUSE_WINDOW_MINUTES} minutes",
        )

    download_count = recent.filter(access_type=MediaAccessLog.DOWNLOAD).count()
    if download_count > MAX_DOWNLOADS_PER_WINDOW:
        _raise_flag(
            log,
            MediaAbuseFlag.TOO_MANY_DOWNLOADS,
            f"{download_count} downloads in {ABUSE_WINDOW_MINUTES} minutes",
        )

    if log.access_type == MediaAccessLog.STREAM:
        repeat_count = recent.filter(
            access_type=MediaAccessLog.STREAM,
            content_type_id=log.content_type_id,
            object_id=log.object_id,
        ).count()
        if repeat_count > MAX_FULL_ACCESS_PER_OBJECT_PER_WINDOW:
            _raise_flag(
                log,
                MediaAbuseFlag.REPEATED_FULL_TRACK_ACCESS,
                f"Object {log.object_id} fully accessed {repeat_count} times "
                f"in {ABUSE_WINDOW_MINUTES} minutes",
            )


def protection_labels(content_object, exclude=()):
    """UI labels describing how a work is protected.

    "Origin Locked" / "Artist Sealed" come from Origin Lock badges once a
    release is sealed; pass those via ``exclude`` to avoid duplicates.
    """
    labels = []
    if getattr(content_object, "public_stream_enabled", False):
        labels.append("Protected Stream")
    consent = getattr(content_object, "ai_training_consent", "")
    if getattr(content_object, "no_ai_training_notice", False) and consent != "allowed":
        labels.append("Do Not Train")
    return [label for label in labels if label not in set(exclude)]


def serialize_protection(content_object, badges=()):
    return {
        "is_master_private": getattr(content_object, "is_master_private", True),
        "public_stream_enabled": getattr(content_object, "public_stream_enabled", False),
        "download_requires_purchase": getattr(content_object, "download_requires_purchase", False),
        "ai_training_consent": getattr(content_object, "ai_training_consent", "unknown"),
        "no_ai_training_notice": getattr(content_object, "no_ai_training_notice", False),
        "labels": protection_labels(content_object, exclude=badges),
        "notice": PROTECTED_WORK_NOTICE,
    }
