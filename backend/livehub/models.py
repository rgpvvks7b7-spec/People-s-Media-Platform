from django.conf import settings
from django.db import models


class LiveSession(models.Model):
    PUBLIC = "public"
    PREVIEW_10 = "preview_10"
    PREVIEW_30 = "preview_30"
    PREVIEW_60 = "preview_60"
    SUPPORTERS = "supporters"

    ACCESS_MODES = [
        (PUBLIC, "Public"),
        (PREVIEW_10, "10 Minute Preview"),
        (PREVIEW_30, "30 Minute Preview"),
        (PREVIEW_60, "60 Minute Preview"),
        (SUPPORTERS, "Supporters Only"),
    ]

    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="live_sessions")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    access_mode = models.CharField(max_length=40, choices=ACCESS_MODES, default=PREVIEW_30)
    is_live = models.BooleanField(default=True)
    viewer_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return self.title


class LiveChatMessage(models.Model):
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author}: {self.body[:40]}"
