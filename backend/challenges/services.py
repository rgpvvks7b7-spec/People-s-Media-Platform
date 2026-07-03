from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import ArtistChallengeProgress, ArtistStreak, ChallengeTemplate, GrowthPoints


DEFAULT_TEMPLATES = [
    {
        "cadence": ChallengeTemplate.DAILY,
        "slug": "post-instant",
        "title": "Post 1 Instant",
        "description": "Show up between releases with a short supporter or follower update.",
        "target_count": 1,
        "metric": "post_instant",
    },
    {
        "cadence": ChallengeTemplate.DAILY,
        "slug": "add-update-pov",
        "title": "Add or update your POV",
        "description": "Sharpen the point of view behind your work.",
        "target_count": 1,
        "metric": "add_update_pov",
    },
    {
        "cadence": ChallengeTemplate.DAILY,
        "slug": "reply-comments",
        "title": "Reply to 3 supporter comments",
        "description": "Reward the fans already engaging with you.",
        "target_count": 3,
        "metric": "reply_comments",
    },
    {
        "cadence": ChallengeTemplate.WEEKLY,
        "slug": "go-live",
        "title": "Go live",
        "description": "Run one live session this week.",
        "target_count": 1,
        "metric": "go_live",
    },
    {
        "cadence": ChallengeTemplate.WEEKLY,
        "slug": "add-public-calendar-items",
        "title": "Add 2 calendar items",
        "description": "Give supporters and fans something concrete to anticipate.",
        "target_count": 2,
        "metric": "calendar_item",
    },
    {
        "cadence": ChallengeTemplate.WEEKLY,
        "slug": "new-subscriber",
        "title": "Get 1 new subscriber",
        "description": "Convert fan attention into direct support.",
        "target_count": 1,
        "metric": "new_subscriber",
    },
    {
        "cadence": ChallengeTemplate.WEEKLY,
        "slug": "book-spaces-gig",
        "title": "Book or confirm a local Spaces gig",
        "description": "Turn local supporters into real-world turnout at a cafe or venue.",
        "target_count": 1,
        "metric": "spaces_booking",
    },
]


def week_start(value):
    return value.date() - timezone.timedelta(days=value.weekday())


def period_start_for(cadence, now=None):
    now = now or timezone.now()
    if cadence == ChallengeTemplate.WEEKLY:
        return week_start(now)
    return now.date()


def ensure_default_templates():
    for data in DEFAULT_TEMPLATES:
        ChallengeTemplate.objects.update_or_create(
            slug=data["slug"],
            defaults={**data, "is_active": True},
        )


def ensure_progress_for_artist(artist, now=None):
    ensure_default_templates()
    now = now or timezone.now()
    progress_rows = []

    for template in ChallengeTemplate.objects.filter(is_active=True):
        progress, _ = ArtistChallengeProgress.objects.get_or_create(
            artist=artist,
            template=template,
            period_start=period_start_for(template.cadence, now),
        )
        progress_rows.append(progress)

    return progress_rows


def update_streak_for_daily_completion(artist, completed_date):
    streak, _ = ArtistStreak.objects.get_or_create(artist=artist)

    if streak.last_completed_date == completed_date:
        return streak

    if streak.last_completed_date == completed_date - timezone.timedelta(days=1):
        streak.current_streak += 1
    else:
        streak.current_streak = 1

    streak.longest_streak = max(streak.longest_streak, streak.current_streak)
    streak.last_completed_date = completed_date
    streak.save(update_fields=["current_streak", "longest_streak", "last_completed_date", "updated_at"])
    return streak


@transaction.atomic
def increment_metric(artist, metric, amount=1, now=None):
    if not artist or not metric:
        return []

    now = now or timezone.now()
    ensure_progress_for_artist(artist, now)
    completed = []

    progress_rows = (
        ArtistChallengeProgress.objects
        .select_for_update()
        .select_related("template")
        .filter(
            artist=artist,
            template__metric=metric,
            template__is_active=True,
            period_start__in=[now.date(), week_start(now)],
            completed_at__isnull=True,
        )
    )

    for progress in progress_rows:
        progress.progress = min(progress.progress + amount, progress.template.target_count)
        if progress.progress >= progress.template.target_count:
            progress.completed_at = now
            completed.append(progress)
            GrowthPoints.objects.create(
                artist=artist,
                points=10 if progress.template.cadence == ChallengeTemplate.DAILY else 30,
                reason=f"Completed challenge: {progress.template.title}",
            )
            if progress.template.cadence == ChallengeTemplate.DAILY:
                update_streak_for_daily_completion(artist, now.date())
        progress.save(update_fields=["progress", "completed_at", "updated_at"])

    return completed


def serialize_progress(progress):
    return {
        "id": progress.id,
        "slug": progress.template.slug,
        "cadence": progress.template.cadence,
        "title": progress.template.title,
        "description": progress.template.description,
        "metric": progress.template.metric,
        "target_count": progress.template.target_count,
        "progress": progress.progress,
        "completed": bool(progress.completed_at),
        "completed_at": progress.completed_at,
        "period_start": progress.period_start,
    }


def get_artist_challenge_board(artist):
    progress_rows = ensure_progress_for_artist(artist)
    streak, _ = ArtistStreak.objects.get_or_create(artist=artist)
    total_points = GrowthPoints.objects.filter(artist=artist).aggregate(total=Sum("points"))["total"] or 0

    return {
        "daily": [
            serialize_progress(row)
            for row in progress_rows
            if row.template.cadence == ChallengeTemplate.DAILY
        ],
        "weekly": [
            serialize_progress(row)
            for row in progress_rows
            if row.template.cadence == ChallengeTemplate.WEEKLY
        ],
        "streak": {
            "current_streak": streak.current_streak,
            "longest_streak": streak.longest_streak,
            "last_completed_date": streak.last_completed_date,
        },
        "growth_points": total_points,
    }
