from django.conf import settings
from django.db import models


class ChallengeTemplate(models.Model):
    DAILY = "daily"
    WEEKLY = "weekly"

    CADENCE_CHOICES = [
        (DAILY, "Daily"),
        (WEEKLY, "Weekly"),
    ]

    cadence = models.CharField(max_length=20, choices=CADENCE_CHOICES)
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    target_count = models.PositiveSmallIntegerField(default=1)
    metric = models.CharField(max_length=60)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["cadence", "slug"]

    def __str__(self):
        return self.title


class ArtistChallengeProgress(models.Model):
    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="challenge_progress")
    template = models.ForeignKey(ChallengeTemplate, on_delete=models.CASCADE, related_name="artist_progress")
    period_start = models.DateField()
    progress = models.PositiveSmallIntegerField(default=0)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("artist", "template", "period_start")
        ordering = ["template__cadence", "template__slug"]
        indexes = [
            models.Index(fields=["artist", "period_start"]),
            models.Index(fields=["template", "period_start"]),
        ]

    def __str__(self):
        return f"{self.artist} {self.template.slug} {self.period_start}"


class ArtistStreak(models.Model):
    artist = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="challenge_streak")
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_completed_date = models.DateField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.artist} streak {self.current_streak}"


class GrowthPoints(models.Model):
    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="growth_points")
    points = models.PositiveSmallIntegerField(default=0)
    reason = models.CharField(max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.artist}: {self.points} {self.reason}"
