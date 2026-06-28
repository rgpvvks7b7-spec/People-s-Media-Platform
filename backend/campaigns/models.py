from decimal import Decimal

from django.conf import settings
from django.db import models


class Campaign(models.Model):
    NEW_SONG = "new_song"
    ALBUM = "album"
    ARTIST_PAGE = "artist_page"
    MERCH = "merch"
    SHOW = "show"
    VIDEO = "video"

    CAMPAIGN_TYPES = [
        (NEW_SONG, "New song"),
        (ALBUM, "Album"),
        (ARTIST_PAGE, "Artist page"),
        (MERCH, "Merch"),
        (SHOW, "Show"),
        (VIDEO, "Video"),
    ]

    MORE_STREAMS = "more_streams"
    NEW_FOLLOWERS = "new_followers"
    EMAIL_SIGNUPS = "email_signups"
    MERCH_SALES = "merch_sales"
    TICKET_SALES = "ticket_sales"
    VIDEO_VIEWS = "video_views"

    GOALS = [
        (MORE_STREAMS, "More streams"),
        (NEW_FOLLOWERS, "New followers"),
        (EMAIL_SIGNUPS, "Email signups"),
        (MERCH_SALES, "Merch sales"),
        (TICKET_SALES, "Ticket sales"),
        (VIDEO_VIEWS, "Video views"),
    ]

    VALID_AD_NETWORKS = {
        "meta",
        "google",
        "youtube",
        "tiktok",
        "spotify",
        "reddit",
        "pinterest",
        "snapchat",
        "x",
    }

    INDIEFUND_PAGE = "indiefund_page"
    SMART_LINK = "smart_link"
    STREAMING_LINK = "streaming_link"
    STORE = "store"
    SIGNUP = "signup"
    EXTERNAL_URL = "external_url"

    DESTINATION_TYPES = [
        (INDIEFUND_PAGE, "IndieFund page"),
        (SMART_LINK, "Smart link"),
        (STREAMING_LINK, "Streaming link"),
        (STORE, "Store"),
        (SIGNUP, "Signup page"),
        (EXTERNAL_URL, "External URL"),
    ]

    DRAFT = "draft"
    READY = "ready"
    LAUNCHED = "launched"
    PAUSED = "paused"
    COMPLETED = "completed"

    STATUSES = [
        (DRAFT, "Draft"),
        (READY, "Ready"),
        (LAUNCHED, "Launched"),
        (PAUSED, "Paused"),
        (COMPLETED, "Completed"),
    ]

    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="growth_campaigns",
    )
    title = models.CharField(max_length=180)
    campaign_type = models.CharField(max_length=40, choices=CAMPAIGN_TYPES, default=NEW_SONG)
    goal = models.CharField(max_length=40, choices=GOALS, default=MORE_STREAMS)
    ad_networks = models.JSONField(default=list, blank=True)
    destination_type = models.CharField(
        max_length=40,
        choices=DESTINATION_TYPES,
        default=SMART_LINK,
    )
    destination_url = models.URLField(max_length=500, blank=True, default="")
    budget_daily = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("10.00"))
    budget_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("300.00"))
    duration_days = models.PositiveIntegerField(default=30)
    audience_description = models.TextField(blank=True, default="")
    similar_artists = models.JSONField(default=list, blank=True)
    locations = models.JSONField(default=list, blank=True)
    age_min = models.PositiveSmallIntegerField(blank=True, null=True)
    age_max = models.PositiveSmallIntegerField(blank=True, null=True)
    creative_headline = models.CharField(max_length=200, blank=True, default="")
    creative_text = models.TextField(blank=True, default="")
    creative_file = models.FileField(upload_to="campaigns/creatives/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUSES, default=DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["artist", "status"]),
        ]

    def __str__(self):
        return f"{self.artist_id} {self.title} ({self.status})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            CampaignMetrics.objects.get_or_create(campaign=self)


class CampaignMetrics(models.Model):
    campaign = models.OneToOneField(
        Campaign,
        on_delete=models.CASCADE,
        related_name="metrics",
    )
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    follows = models.PositiveIntegerField(default=0)
    subscribers = models.PositiveIntegerField(default=0)
    purchases = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    fan_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Metrics for campaign {self.campaign_id}"
