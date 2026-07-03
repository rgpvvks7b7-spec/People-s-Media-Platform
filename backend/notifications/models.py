from django.conf import settings
from django.db import models


class Notification(models.Model):
    POST = "post"
    MUSIC = "music"
    STORE = "store"
    LIVE = "live"
    COMMENT = "comment"
    SUPPORTER = "supporter"
    GIG = "gig"
    PURCHASE = "purchase"
    PROMOTION = "promotion"
    SYSTEM = "system"

    TYPES = [
        (POST, "Post"),
        (MUSIC, "Music"),
        (STORE, "Store"),
        (LIVE, "Live"),
        (COMMENT, "Comment"),
        (SUPPORTER, "Supporter"),
        (GIG, "Gig"),
        (PURCHASE, "Purchase"),
        (PROMOTION, "Promotion"),
        (SYSTEM, "System"),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name="sent_notifications")
    notification_type = models.CharField(max_length=40, choices=TYPES, default=SYSTEM)
    title = models.CharField(max_length=180)
    body = models.TextField(blank=True)
    target_url = models.CharField(max_length=255, blank=True)
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class PushSubscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
    )
    endpoint = models.TextField(unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user_id}:{self.endpoint[:40]}"
