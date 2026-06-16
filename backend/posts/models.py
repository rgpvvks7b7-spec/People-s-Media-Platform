from django.conf import settings
from django.db import models

class Post(models.Model):
    TEXT = "text"
    MUSIC = "music"
    STORY = "story"
    LIVE = "live"

    COMMENT_DEFAULT = "account_default"
    COMMENT_ANYONE = "anyone"
    COMMENT_FOLLOWERS = "followers_subscribers"
    COMMENT_SUBSCRIBERS = "subscribers_only"

    POST_TYPES = [
        (TEXT, "Text"),
        (MUSIC, "Music"),
        (STORY, "Story"),
        (LIVE, "Live"),
    ]

    COMMENT_MODES = [
        (COMMENT_DEFAULT, "Use Artist Default"),
        (COMMENT_ANYONE, "Anyone"),
        (COMMENT_FOLLOWERS, "Supporters"),
        (COMMENT_SUBSCRIBERS, "Subscribers Only"),
    ]

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default=TEXT)
    title = models.CharField(max_length=160, blank=True)
    body = models.TextField(blank=True)
    file = models.FileField(upload_to="posts/", blank=True, null=True)
    is_subscriber_only = models.BooleanField(default=False)
    comment_mode = models.CharField(max_length=40, choices=COMMENT_MODES, default=COMMENT_DEFAULT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"{self.author} post"

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")
