from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from artists.models import ArtistProfile
from .models import Comment, Like, Post
from subscriptions.models import FanSubscription


def is_supporter(user, artist):
    if not user.is_authenticated:
        return False

    return FanSubscription.objects.filter(
        fan=user,
        artist=artist,
        active=True,
    ).exists()


def can_view_post(user, post):
    if user.is_authenticated and user == post.author:
        return True

    if post.is_subscriber_only:
        return is_supporter(user, post.author)

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
        if is_supporter(user, post.author):
            return True, ""
        return False, "Supporters only."

    if mode == Post.COMMENT_SUBSCRIBERS:
        if is_supporter(user, post.author):
            return True, ""
        return False, "Supporters only."

    return False, "Comments are restricted."


def serialize_post(post, request):
    can_comment, comment_block_reason = get_comment_permission(request.user, post)

    return {
        "id": post.id,
        "author_username": post.author.username,
        "post_type": post.post_type,
        "title": post.title,
        "body": post.body,
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

@api_view(["GET"])
def post_list(request):
    posts = Post.objects.select_related("author").order_by("-created_at")

    data = [
        serialize_post(post, request)
        for post in posts
        if can_view_post(request.user, post)
    ]

    return Response(data)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def create_post(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != "artist":
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    post = Post.objects.create(
        author=request.user,
        post_type=request.data.get("post_type", Post.TEXT),
        title=request.data.get("title", ""),
        body=request.data.get("body", ""),
        file=request.FILES.get("file"),
        is_subscriber_only=request.data.get("is_subscriber_only") == "true",
        comment_mode=request.data.get("comment_mode", Post.COMMENT_DEFAULT),
    )

    return Response({
        "message": "Post created",
        "id": post.id,
        "title": post.title,
        "post_type": post.post_type,
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
