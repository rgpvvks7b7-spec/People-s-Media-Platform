from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

_signer = TimestampSigner(salt="mediahub-stream")
_file_signer = TimestampSigner(salt="originlock-file")

# Maps an Origin Lock content kind to the endpoint that serves its file behind a
# signed, expiring token. Raw ``/media/`` URLs are never handed to clients for
# these kinds so downloads can be revoked and time-limited.
FILE_ACCESS_PATHS = {
    "product": "/api/marketplace/files/{object_id}/download/",
    "product_preview": "/api/marketplace/files/{object_id}/preview/",
}


def build_media_stream_token(track_id, access="full"):
    return _signer.sign(f"{track_id}:{access}")


def parse_media_stream_token(token):
    if not token:
        return None, None
    try:
        value = _signer.unsign(token, max_age=settings.MEDIA_STREAM_TOKEN_SECONDS)
    except (BadSignature, SignatureExpired):
        return None, None

    parts = value.split(":", 1)
    if len(parts) != 2:
        return None, None

    try:
        track_id = int(parts[0])
    except (TypeError, ValueError):
        return None, None

    return track_id, parts[1]


def build_stream_url(request, track_id, access="full"):
    token = build_media_stream_token(track_id, access)
    return request.build_absolute_uri(f"/api/media/tracks/{track_id}/stream/?token={token}")


def build_file_access_token(content_kind, object_id, access="full"):
    return _file_signer.sign(f"{content_kind}:{object_id}:{access}")


def parse_file_access_token(token):
    if not token:
        return None, None, None
    try:
        value = _file_signer.unsign(token, max_age=settings.MEDIA_STREAM_TOKEN_SECONDS)
    except (BadSignature, SignatureExpired):
        return None, None, None

    parts = value.split(":")
    if len(parts) != 3:
        return None, None, None

    kind, raw_id, access = parts
    try:
        return kind, int(raw_id), access
    except (TypeError, ValueError):
        return None, None, None


def build_signed_file_url(request, content_kind, object_id, access="full"):
    path = FILE_ACCESS_PATHS.get(content_kind)
    if not path:
        return None
    token = build_file_access_token(content_kind, object_id, access)
    return request.build_absolute_uri(f"{path.format(object_id=object_id)}?token={token}")
