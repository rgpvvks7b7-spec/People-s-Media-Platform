from django.utils import timezone

from artists.models import ArtistFollow, ArtistProfile, FanJourneyEvent
from mediahub.models import AiReviewFlag, MusicUpload
from posts.models import Instant, PointOfView
from subscriptions.models import FanSubscription


PROFILE_COMPLETE_REQUIREMENTS = {
    "avatar": "Add a profile photo",
    "artist_story": "Write your artist story",
    "pov": "Post your point of view",
    "post_or_instant": "Post an update or Instant",
    "city": "Add your city",
    "genre": "Add your genre",
    "social_link": "Link Instagram, TikTok, YouTube, or website",
}

NEW_ARTIST_UPLOAD_LIMIT = 3
NEW_ARTIST_WINDOW_DAYS = 14
HIGH_VELOCITY_UPLOADS_PER_DAY = 8


def artist_has_avatar(user):
    return bool(user.avatar)


def artist_has_story(profile):
    return bool((profile.artist_story or "").strip()) if profile else False


def artist_has_pov(user):
    return PointOfView.objects.filter(artist=user).exists()


def artist_has_presence(user):
    from posts.models import Post

    return (
        Post.objects.filter(author=user).exists()
        or Instant.objects.filter(artist=user).exists()
    )


def artist_has_city(profile):
    return bool((profile.city or "").strip()) if profile else False


def artist_has_genre(profile):
    return bool((profile.genre or "").strip()) if profile else False


def artist_has_social_link(profile):
    if not profile:
        return False
    return any([
        (profile.instagram_url or "").strip(),
        (profile.tiktok_url or "").strip(),
        (profile.youtube_url or "").strip(),
        (profile.website_url or "").strip(),
    ])


def profile_completion(user, profile):
    checks = {
        "avatar": artist_has_avatar(user),
        "artist_story": artist_has_story(profile),
        "pov": artist_has_pov(user),
        "post_or_instant": artist_has_presence(user),
        "city": artist_has_city(profile),
        "genre": artist_has_genre(profile),
        "social_link": artist_has_social_link(profile),
    }
    completed = sum(1 for value in checks.values() if value)
    missing = [
        {"key": key, "label": PROFILE_COMPLETE_REQUIREMENTS[key]}
        for key, done in checks.items()
        if not done
    ]
    return {
        "complete": completed == len(checks),
        "completed_count": completed,
        "required_count": len(checks),
        "missing": missing,
    }


def count_recent_uploads(user, days=1):
    since = timezone.now() - timezone.timedelta(days=days)
    return MusicUpload.objects.filter(artist=user, created_at__gte=since).count()


def count_open_ai_flags(user):
    return AiReviewFlag.objects.filter(
        upload__artist=user,
        status=AiReviewFlag.OPEN,
    ).count()


def compute_bot_risk_score(user, profile):
    score = 0
    reasons = []

    if not profile:
        score += 25
        reasons.append("Missing artist profile")

    completion = profile_completion(user, profile)
    if not completion["complete"]:
        score += 20
        reasons.append("Incomplete profile")

    uploads_24h = count_recent_uploads(user, days=1)
    if uploads_24h >= HIGH_VELOCITY_UPLOADS_PER_DAY:
        score += 35
        reasons.append("High upload velocity")

    total_uploads = MusicUpload.objects.filter(artist=user).count()
    followers = ArtistFollow.objects.filter(artist=user).count() if user else 0
    subscribers = FanSubscription.objects.filter(artist=user, active=True).count()
    if total_uploads >= 10 and subscribers == 0 and followers < 5:
        score += 20
        reasons.append("Many uploads with no supporter traction")

    engagement_events = FanJourneyEvent.objects.filter(
        artist=user,
        event_type=FanJourneyEvent.CONTENT_ENGAGEMENT,
    ).count()
    if total_uploads >= 5 and engagement_events == 0 and not artist_has_pov(user):
        score += 15
        reasons.append("No engagement signals")

    open_flags = count_open_ai_flags(user)
    if open_flags:
        score += min(open_flags * 10, 30)
        reasons.append("Open AI review flags")

    score = min(score, 100)
    if score >= 70:
        level = "high"
    elif score >= 40:
        level = "medium"
    else:
        level = "low"

    return {
        "score": score,
        "level": level,
        "reasons": reasons[:5],
    }


def upload_limit_for_artist(user, profile):
    if not profile:
        return 0, "Complete your artist profile before uploading."

    completion = profile_completion(user, profile)
    account_age = timezone.now() - user.date_joined
    is_new = account_age.days < NEW_ARTIST_WINDOW_DAYS

    risk = compute_bot_risk_score(user, profile)
    if risk["level"] == "high":
        return 0, "Uploads paused pending review. Contact support if this is a mistake."

    if count_open_ai_flags(user) >= 2:
        return 0, "Uploads paused while AI disclosure flags are reviewed."

    if is_new and not completion["complete"]:
        current = MusicUpload.objects.filter(artist=user).count()
        remaining = max(NEW_ARTIST_UPLOAD_LIMIT - current, 0)
        if remaining <= 0:
            return 0, "Complete your profile to unlock unlimited uploads."
        return remaining, f"New artists can upload {remaining} more track(s) until profile is complete."

    return None, ""


def maybe_flag_upload_for_review(track, *, reason):
    if not reason:
        return None
    return AiReviewFlag.objects.create(upload=track, reason=reason[:240])


def evaluate_upload_risk(track):
    artist = track.artist
    profile = getattr(artist, "artist_profile", None)
    reasons = []

    uploads_24h = count_recent_uploads(artist, days=1)
    if uploads_24h >= HIGH_VELOCITY_UPLOADS_PER_DAY:
        reasons.append("High upload velocity in 24h")

    if track.ai_disclosure_level in {MusicUpload.AI_COLLABORATIVE} and uploads_24h >= 3:
        reasons.append("Multiple AI-collaborative uploads in 24h")

    risk = compute_bot_risk_score(artist, profile)
    if risk["level"] == "high":
        reasons.append("Elevated bot risk score")

    if not reasons:
        return None
    return maybe_flag_upload_for_review(track, reason="; ".join(reasons))


def get_artist_trust_status(user):
    profile = getattr(user, "artist_profile", None)
    completion = profile_completion(user, profile)
    risk = compute_bot_risk_score(user, profile)
    remaining, message = upload_limit_for_artist(user, profile)
    open_flags = AiReviewFlag.objects.filter(
        upload__artist=user,
        status=AiReviewFlag.OPEN,
    ).select_related("upload").order_by("-created_at")[:10]

    return {
        "profile_completion": completion,
        "bot_risk": risk,
        "upload_limit_remaining": remaining,
        "upload_limit_message": message,
        "open_ai_review_flags": open_flags.count(),
        "ai_review_flags": [
            {
                "id": flag.id,
                "upload_id": flag.upload_id,
                "upload_title": flag.upload.title,
                "reason": flag.reason,
                "status": flag.status,
                "created_at": flag.created_at,
            }
            for flag in open_flags
        ],
    }
