from decimal import Decimal

from django.db.models import Max, Sum
from django.utils import timezone

from .models import ArtistFollow
from livehub.models import LiveSession
from posts.models import Comment, Post
from subscriptions.models import FanSubscription


def get_artist_business_health(artist, profile=None):
    now = timezone.now()
    start_30d = now - timezone.timedelta(days=30)
    start_90d = now - timezone.timedelta(days=90)

    followers = ArtistFollow.objects.filter(artist=artist).count()
    active_subscriptions = FanSubscription.objects.filter(artist=artist, active=True)
    active_subscribers = active_subscriptions.values("fan_id").distinct().count()
    monthly_artist_share = active_subscriptions.aggregate(total=Sum("artist_share"))["total"] or Decimal("0.00")
    new_subscribers_30d = FanSubscription.objects.filter(
        artist=artist,
        active=True,
        started_at__gte=start_30d,
    ).values("fan_id").distinct().count()
    supporter_ratio = round((active_subscribers / max(followers, 1)) * 100, 2)

    recent_posts = Post.objects.filter(author=artist, created_at__gte=start_90d)
    supporter_posts = recent_posts.filter(is_subscriber_only=True).count()
    posts_count = recent_posts.count()
    artist_comments = Comment.objects.filter(
        author=artist,
        post__author=artist,
        created_at__gte=start_90d,
    ).count()
    live_count = LiveSession.objects.filter(artist=artist, started_at__gte=start_90d).count()
    last_post_at = Post.objects.filter(author=artist).aggregate(last=Max("created_at"))["last"]
    last_live_at = LiveSession.objects.filter(artist=artist).aggregate(last=Max("started_at"))["last"]
    last_comment_at = Comment.objects.filter(author=artist, post__author=artist).aggregate(last=Max("created_at"))["last"]
    last_active_at = max([value for value in [last_post_at, last_live_at, last_comment_at] if value], default=None)

    if profile and profile.on_hiatus:
        badge = "On hiatus"
        engagement_score = 0
    else:
        engagement_score = min((posts_count * 2) + (supporter_posts * 3) + (artist_comments * 2) + (live_count * 3), 20)
        if artist_comments >= 5 or live_count >= 2:
            badge = "Highly responsive"
        elif posts_count >= 4 or supporter_posts >= 2:
            badge = "Active creator"
        elif posts_count >= 1:
            badge = "Building in public"
        else:
            badge = "Quiet lately"

    is_emerging = (
        profile is not None
        and (now - profile.created_at).days < 30
    ) or followers < 10

    return {
        "followers": followers,
        "active_subscribers": active_subscribers,
        "monthly_artist_share": str(monthly_artist_share.quantize(Decimal("0.01"))),
        "new_subscribers_30d": new_subscribers_30d,
        "supporter_ratio": supporter_ratio,
        "supporter_ratio_label": f"{supporter_ratio:g}% supporters",
        "genre_benchmark": "Emerging artists often start below 10%.",
        "engagement": {
            "badge": badge,
            "score": engagement_score,
            "posts_90d": posts_count,
            "supporter_posts_90d": supporter_posts,
            "artist_comments_90d": artist_comments,
            "live_streams_90d": live_count,
            "last_active_at": last_active_at,
            "on_hiatus": bool(profile and profile.on_hiatus),
        },
        "is_emerging": is_emerging,
    }
