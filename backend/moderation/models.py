from django.conf import settings
from django.db import models


class ContentReport(models.Model):
    POST = "post"
    COMMENT = "comment"
    INSTANT = "instant"
    USER = "user"
    ARTIST = "artist"

    TARGET_TYPES = [
        (POST, "Post"),
        (COMMENT, "Comment"),
        (INSTANT, "Instant"),
        (USER, "User"),
        (ARTIST, "Artist profile"),
    ]

    SPAM = "spam"
    HARASSMENT = "harassment"
    INAPPROPRIATE = "inappropriate"
    OTHER = "other"

    REASONS = [
        (SPAM, "Spam"),
        (HARASSMENT, "Harassment"),
        (INAPPROPRIATE, "Inappropriate content"),
        (OTHER, "Other"),
    ]

    OPEN = "open"
    DISMISSED = "dismissed"
    REMOVED = "removed"

    STATUSES = [
        (OPEN, "Open"),
        (DISMISSED, "Dismissed"),
        (REMOVED, "Removed"),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="content_reports_filed",
    )
    target_type = models.CharField(max_length=20, choices=TARGET_TYPES)
    target_id = models.PositiveIntegerField()
    reason = models.CharField(max_length=40, choices=REASONS, default=OTHER)
    details = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default=OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="content_reports_resolved",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.target_type}:{self.target_id} ({self.status})"


class UserBlock(models.Model):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_initiated",
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_received",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("blocker", "blocked")]

    def __str__(self):
        return f"{self.blocker} blocked {self.blocked}"


class UserMute(models.Model):
    muter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mutes_initiated",
    )
    muted = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mutes_received",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("muter", "muted")]

    def __str__(self):
        return f"{self.muter} muted {self.muted}"
