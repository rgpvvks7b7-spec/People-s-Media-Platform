from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from posts.models import Comment, Instant, Post

from .models import ContentReport, UserBlock, UserMute

REPORT_THRESHOLD = 3


def serialize_report(report):
    return {
        "id": report.id,
        "target_type": report.target_type,
        "target_id": report.target_id,
        "reason": report.reason,
        "details": report.details,
        "status": report.status,
        "reporter": report.reporter.username,
        "created_at": report.created_at,
        "resolved_at": report.resolved_at,
    }


def blocked_user_ids(user):
    if not user.is_authenticated:
        return set()
    blocked = set(
        UserBlock.objects.filter(blocker=user).values_list("blocked_id", flat=True)
    )
    blocked |= set(
        UserBlock.objects.filter(blocked=user).values_list("blocker_id", flat=True)
    )
    return blocked


def muted_user_ids(user):
    if not user.is_authenticated:
        return set()
    return set(UserMute.objects.filter(muter=user).values_list("muted_id", flat=True))


def hide_content_for_reports(target_type, target_id):
    open_count = ContentReport.objects.filter(
        target_type=target_type,
        target_id=target_id,
        status=ContentReport.OPEN,
    ).count()
    if open_count < REPORT_THRESHOLD:
        return

    if target_type == ContentReport.POST:
        Post.objects.filter(id=target_id).update(is_hidden=True)
    elif target_type == ContentReport.INSTANT:
        Instant.objects.filter(id=target_id).update(is_hidden=True)
    elif target_type == ContentReport.COMMENT:
        Comment.objects.filter(id=target_id).update(is_hidden=True)


@api_view(["GET", "POST"])
def reports(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == "GET":
        if not request.user.is_staff:
            return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)
        status_filter = request.query_params.get("status") or ContentReport.OPEN
        queryset = ContentReport.objects.select_related("reporter").filter(status=status_filter)[:100]
        return Response({
            "results": [serialize_report(item) for item in queryset],
            "count": queryset.count(),
        })

    target_type = (request.data.get("target_type") or "").strip()
    target_id = request.data.get("target_id")
    reason = (request.data.get("reason") or ContentReport.OTHER).strip()
    details = (request.data.get("details") or "").strip()

    if target_type not in dict(ContentReport.TARGET_TYPES):
        return Response({"error": "Invalid target type"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        target_id = int(target_id)
    except (TypeError, ValueError):
        return Response({"error": "target_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    if reason not in dict(ContentReport.REASONS):
        reason = ContentReport.OTHER

    report = ContentReport.objects.create(
        reporter=request.user,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        details=details,
    )
    hide_content_for_reports(target_type, target_id)

    return Response({
        "message": "Report submitted. Our team will review it.",
        "report": serialize_report(report),
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def resolve_report(request, report_id):
    if not request.user.is_authenticated or not request.user.is_staff:
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    try:
        report = ContentReport.objects.get(id=report_id)
    except ContentReport.DoesNotExist:
        return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)

    action = (request.data.get("action") or "dismiss").strip()
    if action == "remove":
        report.status = ContentReport.REMOVED
        if report.target_type == ContentReport.POST:
            Post.objects.filter(id=report.target_id).update(is_hidden=True)
        elif report.target_type == ContentReport.INSTANT:
            Instant.objects.filter(id=report.target_id).update(is_hidden=True)
        elif report.target_type == ContentReport.COMMENT:
            Comment.objects.filter(id=report.target_id).update(is_hidden=True)
    else:
        report.status = ContentReport.DISMISSED

    report.resolved_at = timezone.now()
    report.resolved_by = request.user
    report.save()

    return Response({
        "message": f"Report {report.status}.",
        "report": serialize_report(report),
    })


@api_view(["GET", "POST"])
def blocks(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == "GET":
        blocked = UserBlock.objects.filter(blocker=request.user).select_related("blocked")
        return Response({
            "results": [{"id": item.blocked.id, "username": item.blocked.username} for item in blocked],
        })

    blocked_id = request.data.get("user_id")
    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        blocked_user = User.objects.get(id=blocked_id)
    except (TypeError, ValueError, User.DoesNotExist):
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    if blocked_user.id == request.user.id:
        return Response({"error": "You cannot block yourself"}, status=status.HTTP_400_BAD_REQUEST)

    UserBlock.objects.get_or_create(blocker=request.user, blocked=blocked_user)
    return Response({"message": f"Blocked {blocked_user.username}."})


@api_view(["POST"])
def unblock(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    blocked_id = request.data.get("user_id")
    UserBlock.objects.filter(blocker=request.user, blocked_id=blocked_id).delete()
    return Response({"message": "User unblocked."})


@api_view(["GET", "POST"])
def mutes(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == "GET":
        muted = UserMute.objects.filter(muter=request.user).select_related("muted")
        return Response({
            "results": [{"id": item.muted.id, "username": item.muted.username} for item in muted],
        })

    muted_id = request.data.get("user_id")
    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        muted_user = User.objects.get(id=muted_id)
    except (TypeError, ValueError, User.DoesNotExist):
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    if muted_user.id == request.user.id:
        return Response({"error": "You cannot mute yourself"}, status=status.HTTP_400_BAD_REQUEST)

    UserMute.objects.get_or_create(muter=request.user, muted=muted_user)
    return Response({"message": f"Muted {muted_user.username}."})


@api_view(["POST"])
def unmute(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    muted_id = request.data.get("user_id")
    UserMute.objects.filter(muter=request.user, muted_id=muted_id).delete()
    return Response({"message": "User unmuted."})
