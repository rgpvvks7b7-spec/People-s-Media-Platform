from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from urllib.parse import urlparse
from django.utils import timezone
from artists.journey import log_fan_journey_event
from artists.models import ArtistFollow, ArtistProfile
from artists.models import FanJourneyEvent
from notifications.services import notify_opted_in_supporters
from .models import Comment, Instant, InstantReport, Like, PointOfView, Post
from subscriptions.models import FanSubscription

MAX_INSTANT_IMAGE_SIZE = 8 * 1024 * 1024
MAX_INSTANT_AUDIO_SIZE = 12 * 1024 * 1024
ALLOWED_INSTANT_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_INSTANT_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}


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


def is_supporter(user, artist, profession=ArtistProfile.DEFAULT_PROFESSION):
    if not user.is_authenticated:
        return False

    return FanSubscription.objects.filter(
        fan=user,
        artist=artist,
        profession=profession,
        active=True,
    ).exists()


def is_follower(user, artist):
    if not user.is_authenticated:
        return False

    return ArtistFollow.objects.filter(fan=user, artist=artist).exists()


def validate_instant_media(file_obj):
    if not file_obj:
        return ""

    name = file_obj.name.lower()
    is_image = any(name.endswith(ext) for ext in ALLOWED_INSTANT_IMAGE_EXTENSIONS)
    is_audio = any(name.endswith(ext) for ext in ALLOWED_INSTANT_AUDIO_EXTENSIONS)

    if not is_image and not is_audio:
        return "Instant media must be an image or short audio file."

    if is_image and file_obj.size > MAX_INSTANT_IMAGE_SIZE:
        return "Instant image is too large."

    if is_audio and file_obj.size > MAX_INSTANT_AUDIO_SIZE:
        return "Instant audio is too large. Use a short clip, max 30 seconds."

    return ""


def can_view_instant(user, instant):
    if user.is_authenticated and user == instant.artist:
        return True

    if instant.expires_at <= timezone.now():
        return False

    if instant.visibility == Instant.PUBLIC:
        return True

    if instant.visibility == Instant.FOLLOWERS:
        return is_follower(user, instant.artist) or is_supporter(user, instant.artist)

    if instant.visibility == Instant.SUPPORTERS:
        return is_supporter(user, instant.artist)

    return False


def can_view_post(user, post):
    if user.is_authenticated and user == post.author:
        return True

    if post.is_subscriber_only:
        return is_supporter(user, post.author, post.profession)

    return True


def get_effective_comment_mode(post):
    if post.comment_mode != Post.COMMENT_DEFAULT:
        return post.comment_mode

    try:
        return post.author.artist_profile.comment_mode
    except ArtistProfile.DoesNotExist:
        return ArtistProfile.COMMENT_SUBSCRIBERS


def get_comment_permission(user, post):
    if not user.is_authenticated:
        return False, "Log in to comment."

    if user == post.author:
        return True, ""

    if not can_view_post(user, post):
        return False, "Supporters only."

    mode = get_effective_comment_mode(post)

    if mode == Post.COMMENT_ANYONE:
        return True, ""

    if mode == Post.COMMENT_FOLLOWERS:
        if is_supporter(user, post.author, post.profession):
            return True, ""
        return False, "Supporters only."

    if mode == Post.COMMENT_SUBSCRIBERS:
        if is_supporter(user, post.author, post.profession):
            return True, ""
        return False, "Supporters only."

    return False, "Comments are restricted."


def serialize_post(post, request):
    can_comment, comment_block_reason = get_comment_permission(request.user, post)

    return {
        "id": post.id,
        "author_username": post.author.username,
        "profession": post.profession,
        "profession_label": ArtistProfile.profession_label(post.profession),
        "post_type": post.post_type,
        "title": post.title,
        "body": post.body,
        "external_url": post.external_url,
        "external_provider": post.external_provider,
        "is_subscriber_only": post.is_subscriber_only,
        "comment_mode": post.comment_mode,
        "effective_comment_mode": get_effective_comment_mode(post),
        "can_comment": can_comment,
        "comment_block_reason": comment_block_reason,
        "file": request.build_absolute_uri(post.file.url) if post.file else None,
        "created_at": post.created_at,
        "likes_count": post.likes.count(),
        "comments_count": post.comments.count(),
        "liked_by_current_user": (
            post.likes.filter(user=request.user).exists()
            if request.user.is_authenticated
            else False
        ),
        "comments": [
            {
                "id": comment.id,
                "author_username": comment.author.username,
                "body": comment.body,
                "created_at": comment.created_at,
            }
            for comment in post.comments.select_related("author").order_by("created_at")
        ],
    }


def serialize_pov(pov):
    return {
        "id": pov.id,
        "artist_id": pov.artist_id,
        "artist_username": pov.artist.username,
        "profession": pov.profession,
        "profession_label": ArtistProfile.profession_label(pov.profession) if pov.profession else "",
        "body": pov.body,
        "is_pinned": pov.is_pinned,
        "created_at": pov.created_at,
    }


def serialize_instant(instant, request):
    return {
        "id": instant.id,
        "artist_id": instant.artist_id,
        "artist_username": instant.artist.username,
        "body": instant.body,
        "media": request.build_absolute_uri(instant.media.url) if instant.media else None,
        "visibility": instant.visibility,
        "expires_at": instant.expires_at,
        "created_at": instant.created_at,
        "reports_count": instant.reports.count() if request.user.is_authenticated and request.user == instant.artist else None,
    }

@api_view(["GET"])
def post_list(request):
    posts = Post.objects.select_related("author").filter(is_hidden=False).order_by("-created_at")

    data = [
        serialize_post(post, request)
        for post in posts
        if can_view_post(request.user, post)
    ]

    return Response(data)


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser])
def point_of_view_list(request):
    if request.method == "GET":
        povs = PointOfView.objects.select_related("artist")
        artist_id = request.query_params.get("artist_id")
        profession = request.query_params.get("profession")
        if artist_id:
            povs = povs.filter(artist_id=artist_id)
        if profession:
            povs = povs.filter(profession__in=["", profession])

        return Response({
            "results": [serialize_pov(pov) for pov in povs[:50]],
            "count": povs.count(),
        })

    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != "artist":
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    body = (request.data.get("body") or "").strip()
    if not body:
        return Response({"error": "Point of view is required."}, status=status.HTTP_400_BAD_REQUEST)

    if len(body) > 500:
        return Response({"error": "Point of view must be 500 characters or fewer."}, status=status.HTTP_400_BAD_REQUEST)

    profession_value = (request.data.get("profession") or "").strip()
    profession = ""
    if profession_value:
        profession = normalize_profession(request.user, profession_value)
        if not profession:
            return Response({"error": "Artist does not offer this profession"}, status=status.HTTP_400_BAD_REQUEST)

    is_pinned = str(request.data.get("is_pinned", "true")).lower() in {"1", "true", "yes", "on"}
    if is_pinned:
        PointOfView.objects.filter(
            artist=request.user,
            profession=profession,
            is_pinned=True,
        ).update(is_pinned=False)

    pov = PointOfView.objects.create(
        artist=request.user,
        profession=profession,
        body=body,
        is_pinned=is_pinned,
    )
    from challenges.services import increment_metric
    increment_metric(request.user, "add_update_pov")

    return Response({
        "message": "Point of view saved.",
        "point_of_view": serialize_pov(pov),
    }, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser])
def instant_list(request):
    if request.method == "GET":
        instants = Instant.objects.select_related("artist").prefetch_related("reports").filter(
            expires_at__gt=timezone.now(),
            is_hidden=False,
        )
        artist_id = request.query_params.get("artist_id")
        if artist_id:
            instants = instants.filter(artist_id=artist_id)

        visible_instants = [
            instant for instant in instants[:100]
            if can_view_instant(request.user, instant)
        ]
        visible_instants.sort(
            key=lambda instant: (
                0 if instant.visibility == Instant.SUPPORTERS else 1,
                -instant.created_at.timestamp(),
            )
        )
        return Response({
            "results": [serialize_instant(instant, request) for instant in visible_instants],
            "count": len(visible_instants),
        })

    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != "artist":
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    body = (request.data.get("body") or "").strip()
    if not body:
        return Response({"error": "Instant body is required."}, status=status.HTTP_400_BAD_REQUEST)

    if len(body) > 280:
        return Response({"error": "Instant body must be 280 characters or fewer."}, status=status.HTTP_400_BAD_REQUEST)

    visibility = request.data.get("visibility") or Instant.FOLLOWERS
    if visibility not in dict(Instant.VISIBILITY_CHOICES):
        return Response({"error": "Invalid instant visibility."}, status=status.HTTP_400_BAD_REQUEST)

    media = request.FILES.get("media")
    media_error = validate_instant_media(media)
    if media_error:
        return Response({"error": media_error}, status=status.HTTP_400_BAD_REQUEST)

    try:
        lifetime_hours = int(request.data.get("lifetime_hours") or 24)
    except (TypeError, ValueError):
        lifetime_hours = 24
    lifetime_hours = max(1, min(lifetime_hours, 24 * 7))

    instant = Instant.objects.create(
        artist=request.user,
        body=body,
        media=media,
        visibility=visibility,
        expires_at=timezone.now() + timezone.timedelta(hours=lifetime_hours),
    )
    from challenges.services import increment_metric
    increment_metric(request.user, "post_instant")

    return Response({
        "message": "Instant posted.",
        "instant": serialize_instant(instant, request),
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def report_instant(request, instant_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        instant = Instant.objects.select_related("artist").get(id=instant_id)
    except Instant.DoesNotExist:
        return Response({"error": "Instant not found"}, status=status.HTTP_404_NOT_FOUND)

    if not can_view_instant(request.user, instant):
        return Response({"error": "Instant not found"}, status=status.HTTP_404_NOT_FOUND)

    report, created = InstantReport.objects.get_or_create(
        instant=instant,
        reporter=request.user,
        defaults={"reason": (request.data.get("reason") or "").strip()[:240]},
    )

    return Response({
        "message": "Report received." if created else "Report already received.",
        "report_id": report.id,
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


def get_external_provider(url):
    host = urlparse(url).netloc.lower()

    if host.startswith("www."):
        host = host[4:]

    if host in {"instagram.com", "instagr.am"} or host.endswith(".instagram.com"):
        return Post.INSTAGRAM

    if host in {"tiktok.com", "vm.tiktok.com", "vt.tiktok.com"} or host.endswith(".tiktok.com"):
        return Post.TIKTOK

    return ""


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def create_post(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != "artist":
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    post_type = request.data.get("post_type", Post.TEXT)
    external_url = (request.data.get("external_url") or "").strip()
    external_provider = get_external_provider(external_url) if external_url else ""

    if post_type == Post.TEXT and external_provider in {Post.INSTAGRAM, Post.TIKTOK}:
        post_type = external_provider

    if post_type in {Post.INSTAGRAM, Post.TIKTOK}:
        if not external_url:
            return Response({"error": "Social post URL is required."}, status=status.HTTP_400_BAD_REQUEST)

        if external_provider != post_type:
            return Response({"error": f"Paste a valid {post_type.title()} URL."}, status=status.HTTP_400_BAD_REQUEST)

    profession = normalize_profession(request.user, request.data.get("profession"))
    if not profession:
        return Response({"error": "Artist does not offer this profession"}, status=status.HTTP_400_BAD_REQUEST)

    post = Post.objects.create(
        author=request.user,
        profession=profession,
        post_type=post_type,
        title=request.data.get("title", ""),
        body=request.data.get("body", ""),
        file=request.FILES.get("file"),
        external_url=external_url,
        external_provider=external_provider,
        is_subscriber_only=request.data.get("is_subscriber_only") == "true",
        comment_mode=request.data.get("comment_mode", Post.COMMENT_DEFAULT),
    )
    notify_opted_in_supporters(
        request.user,
        notification_type="post",
        title=f"New post: {post.title or 'Update'}",
        body=(post.body or "New supporter update.")[:240],
        target_url=f"/?artist={request.user.username}",
    )

    return Response({
        "message": "Post created",
        "id": post.id,
        "title": post.title,
        "post_type": post.post_type,
        "post": serialize_post(post, request),
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def create_comment(request, post_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    body = (request.data.get("body") or "").strip()
    if not body:
        return Response({"error": "Comment body is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

    can_comment, comment_block_reason = get_comment_permission(request.user, post)
    if not can_comment:
        return Response({"error": comment_block_reason}, status=status.HTTP_403_FORBIDDEN)

    comment = Comment.objects.create(
        post=post,
        author=request.user,
        body=body,
    )
    if request.user != post.author:
        log_fan_journey_event(
            FanJourneyEvent.CONTENT_ENGAGEMENT,
            post.author,
            fan=request.user,
            metadata={"engagement_type": "comment", "post_id": post.id},
        )

    return Response({
        "message": "Comment created",
        "comment": {
            "id": comment.id,
            "author_username": comment.author.username,
            "body": comment.body,
            "created_at": comment.created_at,
        },
        "comments_count": post.comments.count(),
        "likes_count": post.likes.count(),
        "liked_by_current_user": post.likes.filter(user=request.user).exists(),
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def toggle_like(request, post_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

    if not can_view_post(request.user, post):
        return Response({"error": "Supporters only."}, status=status.HTTP_403_FORBIDDEN)

    like, created = Like.objects.get_or_create(
        post=post,
        user=request.user,
    )

    if created:
        liked = True
        message = "Post liked"
        if request.user != post.author:
            log_fan_journey_event(
                FanJourneyEvent.CONTENT_ENGAGEMENT,
                post.author,
                fan=request.user,
                metadata={"engagement_type": "like", "post_id": post.id},
            )
    else:
        like.delete()
        liked = False
        message = "Post unliked"

    return Response({
        "message": message,
        "liked": liked,
        "comments_count": post.comments.count(),
        "likes_count": post.likes.count(),
        "liked_by_current_user": liked,
    })


@api_view(["POST", "DELETE"])
def delete_post(request, post_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

    if post.author_id != request.user.id and not request.user.is_staff:
        return Response({"error": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

    post.is_hidden = True
    post.save(update_fields=["is_hidden"])
    return Response({"message": "Post removed."})


@api_view(["POST", "DELETE"])
def delete_instant(request, instant_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        instant = Instant.objects.get(id=instant_id)
    except Instant.DoesNotExist:
        return Response({"error": "Instant not found"}, status=status.HTTP_404_NOT_FOUND)

    if instant.artist_id != request.user.id and not request.user.is_staff:
        return Response({"error": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

    instant.is_hidden = True
    instant.save(update_fields=["is_hidden"])
    return Response({"message": "Instant removed."})
