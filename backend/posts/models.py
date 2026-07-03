from django.conf import settings
from django.db import models
from artists.models import ArtistProfile

class Post(models.Model):
    TEXT = "text"
    MUSIC = "music"
    STORY = "story"
    LIVE = "live"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"

    COMMENT_DEFAULT = "account_default"
    COMMENT_ANYONE = "anyone"
    COMMENT_FOLLOWERS = "followers_subscribers"
    COMMENT_SUBSCRIBERS = "subscribers_only"

    POST_TYPES = [
        (TEXT, "Text"),
        (MUSIC, "Music"),
        (STORY, "Story"),
        (LIVE, "Live"),
        (INSTAGRAM, "Instagram Embed"),
        (TIKTOK, "TikTok Embed"),
    ]

    COMMENT_MODES = [
        (COMMENT_DEFAULT, "Use Artist Default"),
        (COMMENT_ANYONE, "Anyone"),
        (COMMENT_FOLLOWERS, "Supporters"),
        (COMMENT_SUBSCRIBERS, "Subscribers Only"),
    ]

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    profession = models.CharField(
        max_length=40,
        choices=ArtistProfile.PROFESSION_CHOICES,
        default=ArtistProfile.DEFAULT_PROFESSION,
    )
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default=TEXT)
    title = models.CharField(max_length=160, blank=True)
    body = models.TextField(blank=True)
    file = models.FileField(upload_to="posts/", blank=True, null=True)
    external_url = models.URLField(blank=True)
    external_provider = models.CharField(max_length=40, blank=True)
    is_subscriber_only = models.BooleanField(default=False)
    comment_mode = models.CharField(max_length=40, choices=COMMENT_MODES, default=COMMENT_DEFAULT)
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"{self.author} post"

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")


class PointOfView(models.Model):
    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="points_of_view")
    profession = models.CharField(
        max_length=40,
        choices=ArtistProfile.PROFESSION_CHOICES,
        blank=True,
    )
    body = models.TextField(max_length=500)
    is_pinned = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.artist} POV"


class Instant(models.Model):
    FOLLOWERS = "followers"
    SUPPORTERS = "supporters"
    PUBLIC = "public"

    VISIBILITY_CHOICES = [
        (FOLLOWERS, "Followers"),
        (SUPPORTERS, "Supporters"),
        (PUBLIC, "Public"),
    ]

    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="instants")
    body = models.TextField(max_length=280)
    media = models.FileField(upload_to="instants/", blank=True, null=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default=FOLLOWERS)
    expires_at = models.DateTimeField()
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["artist", "expires_at"]),
            models.Index(fields=["visibility", "expires_at"]),
        ]

    def __str__(self):
        return f"{self.artist} instant"

    @property
    def is_expired(self):
        from django.utils import timezone

        return self.expires_at <= timezone.now()


class InstantReport(models.Model):
    instant = models.ForeignKey(Instant, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="instant_reports")
    reason = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("instant", "reporter")
        ordering = ["-created_at"]
