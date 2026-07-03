"""Origin Lock services: hashing, approval gating, and sealing."""

import hashlib

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import ReleaseApproval
from .webauthn import verify_assertion

CHUNK_SIZE = 65536


class SealError(Exception):
    """Raised when a release cannot be sealed. ``code`` maps to an HTTP status."""

    def __init__(self, message, code=400):
        super().__init__(message)
        self.message = message
        self.code = code


def compute_file_sha256(file_obj):
    if not file_obj:
        return ""
    hasher = hashlib.sha256()
    try:
        file_obj.seek(0)
    except (AttributeError, ValueError, OSError):
        pass
    for chunk in file_obj.chunks(CHUNK_SIZE) if hasattr(file_obj, "chunks") else iter(lambda: file_obj.read(CHUNK_SIZE), b""):
        hasher.update(chunk)
    try:
        file_obj.seek(0)
    except (AttributeError, ValueError, OSError):
        pass
    return hasher.hexdigest()


def release_file(content_object):
    """Return the FileField that a release approval protects, if any."""
    for attr in ("audio_file", "product_file"):
        field = getattr(content_object, attr, None)
        if field:
            return field
    return None


def create_pending_approval(artist, content_object, file_obj=None, file_name="", *, ai_usage_status=""):
    content_type = ContentType.objects.get_for_model(type(content_object))
    file_hash = compute_file_sha256(file_obj) if file_obj is not None else ""
    approval, _ = ReleaseApproval.objects.get_or_create(
        content_type=content_type,
        object_id=content_object.pk,
        defaults={
            "artist": artist,
            "file_hash": file_hash,
            "file_name": (file_name or "")[:255],
            "ai_usage_status": ai_usage_status,
        },
    )
    return approval


def get_approval_for(content_object):
    if content_object is None or content_object.pk is None:
        return None
    content_type = ContentType.objects.get_for_model(type(content_object))
    return ReleaseApproval.objects.filter(
        content_type=content_type,
        object_id=content_object.pk,
    ).first()


def approvals_for(model, ids):
    """Return a ``{object_id: ReleaseApproval}`` map to avoid per-row lookups."""
    if not ids:
        return {}
    content_type = ContentType.objects.get_for_model(model)
    approvals = ReleaseApproval.objects.filter(content_type=content_type, object_id__in=ids)
    return {approval.object_id: approval for approval in approvals}


def is_publicly_released(content_object):
    approval = get_approval_for(content_object)
    if approval is None:
        return True
    return approval.approval_status == ReleaseApproval.APPROVED


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def seal_release(approval, user, request, *, method, payload=None):
    payload = payload or {}

    if approval.approval_status == ReleaseApproval.APPROVED:
        raise SealError("This release is already sealed.", code=400)

    profile = getattr(approval.artist, "artist_profile", None)
    if user != approval.artist or profile is None or not profile.is_verified:
        raise SealError(
            "Platform verification required before you can seal releases.",
            code=403,
        )

    content_object = approval.content_object
    file_field = release_file(content_object) if content_object is not None else None
    if approval.file_hash and file_field is not None:
        current_hash = compute_file_sha256(file_field.open("rb"))
        if current_hash != approval.file_hash:
            raise SealError(
                "This file changed since upload. Re-upload before sealing.",
                code=409,
            )

    if method == ReleaseApproval.PASSKEY:
        credential = verify_assertion(user, payload.get("passkey"))
        if credential is None:
            raise SealError("Passkey verification failed.", code=400)
    elif method == ReleaseApproval.PASSWORD_FALLBACK:
        if not user.check_password(payload.get("password") or ""):
            raise SealError("Incorrect password.", code=400)
    elif method == ReleaseApproval.ADMIN:
        if not user.is_staff:
            raise SealError("Admin access required.", code=403)
    else:
        raise SealError("Unsupported approval method.", code=400)

    approval.user = user
    approval.approval_method = method
    approval.approval_status = ReleaseApproval.APPROVED
    approval.approved_at = timezone.now()
    approval.ip_address = _client_ip(request)
    approval.user_agent = request.META.get("HTTP_USER_AGENT", "")[:400]
    approval.ai_usage_status = payload.get("ai_usage_status", approval.ai_usage_status)
    approval.rights_owner = (payload.get("rights_owner") or approval.rights_owner)[:200]
    approval.writer_credits = payload.get("writer_credits", approval.writer_credits)
    approval.producer_credits = payload.get("producer_credits", approval.producer_credits)
    approval.ai_training_consent = bool(payload.get("ai_training_consent", approval.ai_training_consent))
    approval.origin_notes = payload.get("origin_notes", approval.origin_notes)
    approval.save()

    _notify_release_sealed(approval)
    return approval


def _notify_release_sealed(approval):
    from marketplace.models import Product
    from mediahub.models import MusicUpload
    from notifications.services import notify_opted_in_supporters

    content_object = approval.content_object
    artist = approval.artist
    display = artist.display_name or artist.username

    if isinstance(content_object, MusicUpload):
        notify_opted_in_supporters(
            artist,
            notification_type="music",
            title=f"New track: {content_object.title}",
            body=f"{display} published new music.",
            target_url=f"/?artist={artist.username}",
        )
    elif isinstance(content_object, Product):
        notify_opted_in_supporters(
            artist,
            notification_type="store",
            title=f"New store drop: {content_object.title}",
            body=f"{display} added a new item.",
            target_url=f"/?artist={artist.username}",
        )


def origin_badges(approval):
    if approval is None or approval.approval_status != ReleaseApproval.APPROVED:
        return []
    badges = ["Origin Locked", "Artist Sealed"]
    if approval.approval_method == ReleaseApproval.PASSKEY:
        badges.append("Human Verified")
    if approval.ai_training_consent:
        badges.append("Do Not Train")
    return badges


def serialize_origin_lock(approval):
    if approval is None:
        return None
    return {
        "id": approval.id,
        "release_status": approval.approval_status,
        "approval_method": approval.approval_method,
        "approved_at": approval.approved_at,
        "file_name": approval.file_name,
        "rights_owner": approval.rights_owner,
        "ai_usage_status": approval.ai_usage_status,
        "writer_credits": approval.writer_credits,
        "producer_credits": approval.producer_credits,
        "ai_training_consent": approval.ai_training_consent,
        "origin_notes": approval.origin_notes,
        "badges": origin_badges(approval),
    }
