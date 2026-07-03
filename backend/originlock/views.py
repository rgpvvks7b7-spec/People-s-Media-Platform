from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import PasskeyCredential, ReleaseApproval, WebAuthnChallenge
from .services import SealError, seal_release, serialize_origin_lock
from .webauthn import consume_challenge, issue_challenge


def _content_kind(approval):
    label = approval.content_type.model if approval.content_type_id else ""
    if label == "musicupload":
        return "track"
    if label == "product":
        return "product"
    return label


def _content_title(approval):
    content_object = approval.content_object
    return getattr(content_object, "title", "") if content_object is not None else ""


def serialize_approval_detail(approval):
    payload = serialize_origin_lock(approval)
    payload.update({
        "artist_username": approval.artist.username,
        "artist_display_name": approval.artist.display_name or approval.artist.username,
        "content_kind": _content_kind(approval),
        "content_title": _content_title(approval),
        "created_at": approval.created_at,
    })
    return payload


@api_view(["GET"])
def pending_releases(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    approvals = (
        ReleaseApproval.objects
        .filter(artist=request.user, approval_status=ReleaseApproval.PENDING)
        .select_related("content_type", "artist")
    )
    return Response({
        "results": [serialize_approval_detail(item) for item in approvals],
        "count": approvals.count(),
    })


@api_view(["GET"])
def release_detail(request, approval_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        approval = ReleaseApproval.objects.select_related("content_type", "artist").get(
            id=approval_id,
            artist=request.user,
        )
    except ReleaseApproval.DoesNotExist:
        return Response({"error": "Release not found"}, status=status.HTTP_404_NOT_FOUND)

    return Response(serialize_approval_detail(approval))


@api_view(["POST"])
def seal_release_view(request, approval_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        approval = ReleaseApproval.objects.select_related("content_type", "artist").get(id=approval_id)
    except ReleaseApproval.DoesNotExist:
        return Response({"error": "Release not found"}, status=status.HTTP_404_NOT_FOUND)

    method = (request.data.get("approval_method") or ReleaseApproval.PASSKEY).strip()
    payload = {
        "passkey": request.data.get("passkey"),
        "password": request.data.get("password"),
        "ai_usage_status": request.data.get("ai_usage_status", ""),
        "rights_owner": request.data.get("rights_owner", ""),
        "writer_credits": request.data.get("writer_credits", ""),
        "producer_credits": request.data.get("producer_credits", ""),
        "ai_training_consent": request.data.get("ai_training_consent") in {True, "true", "1", "on"},
        "origin_notes": request.data.get("origin_notes", ""),
    }

    try:
        approval = seal_release(approval, request.user, request, method=method, payload=payload)
    except SealError as exc:
        return Response({"error": exc.message}, status=exc.code)

    return Response({
        "message": "Release sealed.",
        "origin_lock": serialize_approval_detail(approval),
    })


@api_view(["POST"])
def passkey_register_begin(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    challenge = issue_challenge(request.user, WebAuthnChallenge.REGISTER)
    return Response({
        "challenge": challenge,
        "rp_name": "IndieFund",
        "user_id": str(request.user.id),
        "user_name": request.user.username,
        "note": "Passkeys verify you on-device. No biometric data is sent to or stored by IndieFund.",
    })


@api_view(["POST"])
def passkey_register_complete(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    challenge = request.data.get("challenge")
    credential_id = (request.data.get("credential_id") or "").strip()
    if not credential_id:
        return Response({"error": "credential_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    if not consume_challenge(request.user, WebAuthnChallenge.REGISTER, challenge):
        return Response({"error": "Invalid or expired registration challenge"}, status=status.HTTP_400_BAD_REQUEST)

    credential, _ = PasskeyCredential.objects.update_or_create(
        credential_id=credential_id,
        defaults={
            "user": request.user,
            "public_key": request.data.get("public_key", ""),
            "label": (request.data.get("label") or "").strip()[:120],
        },
    )
    return Response({
        "message": "Passkey registered.",
        "credential_id": credential.credential_id,
        "label": credential.label,
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def passkey_authenticate_begin(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    challenge = issue_challenge(request.user, WebAuthnChallenge.AUTHENTICATE)
    credentials = list(
        PasskeyCredential.objects.filter(user=request.user).values_list("credential_id", flat=True)
    )
    return Response({
        "challenge": challenge,
        "credential_ids": credentials,
    })


@api_view(["GET"])
def passkey_list(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    credentials = PasskeyCredential.objects.filter(user=request.user).order_by("-created_at")
    return Response({
        "results": [
            {
                "credential_id": item.credential_id,
                "label": item.label,
                "created_at": item.created_at,
                "last_used_at": item.last_used_at,
            }
            for item in credentials
        ],
    })
