from django.conf import settings
from django.db import models

class ArtistProfile(models.Model):
    COMMENT_ANYONE = "anyone"
    COMMENT_FOLLOWERS = "followers_subscribers"
    COMMENT_SUBSCRIBERS = "subscribers_only"

    STREAM_PUBLIC = "public"
    STREAM_10 = "public_10"
    STREAM_30 = "public_30"
    STREAM_60 = "public_60"
    STREAM_SUBSCRIBERS = "subscribers_only"

    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="artist_profile")
    stage_name = models.CharField(max_length=120)
    genre = models.CharField(max_length=80, blank=True)
    city = models.CharField(max_length=80, blank=True)
    hero_image = models.ImageField(upload_to="artist_hero/", blank=True, null=True)
    artist_story = models.TextField(blank=True)
    influences = models.CharField(max_length=255, blank=True)
    is_verified = models.BooleanField(default=False)

    comment_mode = models.CharField(max_length=40, default=COMMENT_SUBSCRIBERS, choices=[
        (COMMENT_ANYONE, "Anyone"),
        (COMMENT_FOLLOWERS, "Followers and Subscribers"),
        (COMMENT_SUBSCRIBERS, "Subscribers Only"),
    ])

    livestream_mode = models.CharField(max_length=40, default=STREAM_30, choices=[
        (STREAM_PUBLIC, "Entire Stream Public"),
        (STREAM_10, "Public Preview - 10 Minutes"),
        (STREAM_30, "Public Preview - 30 Minutes"),
        (STREAM_60, "Public Preview - 60 Minutes"),
        (STREAM_SUBSCRIBERS, "Subscribers Only From Start"),
    ])

    created_at = models.DateTimeField(auto_now_add=True)

    show_music = models.BooleanField(default=True)
    show_posts = models.BooleanField(default=True)
    show_store = models.BooleanField(default=True)
    show_lives = models.BooleanField(default=True)
    show_about = models.BooleanField(default=True)


    def __str__(self):
        return self.stage_name


class ArtistFollow(models.Model):
    fan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="artist_follows"
    )

    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="artist_followers"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("fan", "artist")
