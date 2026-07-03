from django.conf import settings
from django.db import models
from django.utils import timezone

from artists.themes import DEFAULT_THEME, THEME_CHOICES

class ArtistProfile(models.Model):
    MUSIC = "music"
    VISUAL_ART = "visual_art"
    DIGITAL_ART = "digital_art"
    CRAFT = "craft"
    WRITING = "writing"
    PERFORMANCE = "performance"
    COMEDY = "comedy"
    PODCAST = "podcast"
    FILM = "film"
    OTHER = "other"

    PROFESSION_CHOICES = [
        (MUSIC, "Music"),
        (VISUAL_ART, "Painting / Drawing"),
        (DIGITAL_ART, "Digital Art"),
        (CRAFT, "Crafts"),
        (WRITING, "Writing"),
        (PERFORMANCE, "Performance"),
        (COMEDY, "Comedian"),
        (PODCAST, "Podcaster"),
        (FILM, "Filmmaker / Video"),
        (OTHER, "Other"),
    ]
    DEFAULT_PROFESSION = MUSIC
    MUSIC_BRANCH_PROFESSIONS = {MUSIC, PERFORMANCE, COMEDY, PODCAST, FILM}

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
    instagram_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)
    is_verified = models.BooleanField(default=False)
    professions = models.CharField(max_length=255, default=DEFAULT_PROFESSION)

    comment_mode = models.CharField(max_length=40, default=COMMENT_SUBSCRIBERS, choices=[
        (COMMENT_ANYONE, "Anyone"),
        (COMMENT_FOLLOWERS, "Supporters"),
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

    youtube_channel_id = models.CharField(max_length=64, blank=True, help_text="Resolved from the YouTube URL")
    youtube_subscriber_count = models.BigIntegerField(blank=True, null=True, help_text="Platform-verified subscriber count from the YouTube Data API")
    youtube_reach_synced_at = models.DateTimeField(blank=True, null=True)
    website_label = models.CharField(max_length=40, blank=True, help_text="e.g. Official Site")
    on_hiatus = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    show_music = models.BooleanField(default=True)
    show_posts = models.BooleanField(default=True)
    show_store = models.BooleanField(default=True)
    show_lives = models.BooleanField(default=True)
    show_about = models.BooleanField(default=True)
    stripe_connect_account_id = models.CharField(max_length=255, blank=True, default="")
    stripe_connect_onboarded_at = models.DateTimeField(blank=True, null=True)

    theme_name = models.CharField(max_length=40, choices=THEME_CHOICES, default=DEFAULT_THEME)
    studio_theme_name = models.CharField(max_length=40, choices=THEME_CHOICES, default=DEFAULT_THEME)


    def __str__(self):
        return self.stage_name

    @classmethod
    def valid_profession_keys(cls):
        return {key for key, _ in cls.PROFESSION_CHOICES}

    @classmethod
    def profession_label(cls, profession):
        return dict(cls.PROFESSION_CHOICES).get(profession, "Music")

    @classmethod
    def is_music_branch_profession(cls, profession):
        return profession in cls.MUSIC_BRANCH_PROFESSIONS

    def profession_list(self):
        valid_keys = self.valid_profession_keys()
        items = [
            item.strip()
            for item in (self.professions or "").split(",")
            if item.strip() in valid_keys
        ]
        return items or [self.DEFAULT_PROFESSION]

    def has_profession(self, profession):
        return profession in self.profession_list()

    @staticmethod
    def format_reach(count):
        if count is None:
            return ""
        count = int(count)
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M".replace(".0M", "M")
        if count >= 1_000:
            return f"{count / 1_000:.1f}K".replace(".0K", "K")
        return str(count)

    def has_youtube_url(self):
        return bool((self.youtube_url or "").strip())

    def youtube_reach_verified(self):
        return self.has_youtube_url() and self.youtube_subscriber_count is not None

    def youtube_reach_display(self):
        if not self.has_youtube_url():
            return ""
        return self.format_reach(self.youtube_subscriber_count)

    def youtube_reach_pending(self):
        return self.has_youtube_url() and self.youtube_subscriber_count is None


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


class ArtistFanContact(models.Model):
    SIGNUP_OPT_IN = "signup_opt_in"
    SUPPORT_PROMPT = "support_prompt"
    MANUAL = "manual"

    SOURCES = [
        (SIGNUP_OPT_IN, "Signup opt-in"),
        (SUPPORT_PROMPT, "Support prompt"),
        (MANUAL, "Manual"),
    ]

    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fan_contacts",
    )
    fan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="artist_contact_permissions",
    )
    email_shared = models.BooleanField(default=False)
    shared_at = models.DateTimeField(blank=True, null=True)
    revoked_at = models.DateTimeField(blank=True, null=True)
    source = models.CharField(max_length=40, choices=SOURCES, default=MANUAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("artist", "fan")
        ordering = ["-shared_at", "-created_at"]

    def share(self, source):
        self.email_shared = True
        self.shared_at = self.shared_at or timezone.now()
        self.revoked_at = None
        self.source = source

    def revoke(self):
        self.email_shared = False
        self.revoked_at = timezone.now()

    def __str__(self):
        return f"{self.fan} email permission for {self.artist}"


class FanJourneyEvent(models.Model):
    PAGE_VIEW = "page_view"
    FOLLOW = "follow"
    SUBSCRIBE = "subscribe"
    TIP = "tip"
    PURCHASE = "purchase"
    MUSIC_PREVIEW = "music_preview"
    MUSIC_FULL_PLAY = "music_full_play"
    EMAIL_OPT_IN = "email_opt_in"
    UNSUBSCRIBE = "unsubscribe"
    CONTENT_ENGAGEMENT = "content_engagement"

    EVENT_TYPES = [
        (PAGE_VIEW, "Page view"),
        (FOLLOW, "Follow"),
        (SUBSCRIBE, "Subscribe"),
        (TIP, "Tip"),
        (PURCHASE, "Purchase"),
        (MUSIC_PREVIEW, "Music preview"),
        (MUSIC_FULL_PLAY, "Music full play"),
        (EMAIL_OPT_IN, "Email opt-in"),
        (UNSUBSCRIBE, "Unsubscribe"),
        (CONTENT_ENGAGEMENT, "Content engagement"),
    ]

    fan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="fan_journey_events",
    )
    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="artist_journey_events",
    )
    event_type = models.CharField(max_length=40, choices=EVENT_TYPES)
    music_upload = models.ForeignKey(
        "mediahub.MusicUpload",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="journey_events",
    )
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["artist", "event_type", "occurred_at"]),
            models.Index(fields=["fan", "artist", "occurred_at"]),
            models.Index(fields=["music_upload", "event_type", "occurred_at"]),
        ]
        ordering = ["-occurred_at"]


class ArtistJourneyRollup(models.Model):
    DAILY = "daily"
    WEEKLY = "weekly"

    PERIODS = [
        (DAILY, "Daily"),
        (WEEKLY, "Weekly"),
    ]

    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="journey_rollups",
    )
    period = models.CharField(max_length=20, choices=PERIODS, default=DAILY)
    period_start = models.DateField()
    event_type = models.CharField(max_length=40, choices=FanJourneyEvent.EVENT_TYPES)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("artist", "period", "period_start", "event_type")
        indexes = [
            models.Index(fields=["artist", "period", "period_start"]),
        ]


class ArtistProfessionProfile(models.Model):
    VISITOR_BANNER_DURATION_CHOICES = (
        (15, "15 seconds"),
        (30, "30 seconds"),
        (45, "45 seconds"),
    )
    VISITOR_BANNER_DURATIONS = {choice[0] for choice in VISITOR_BANNER_DURATION_CHOICES}

    artist_profile = models.ForeignKey(
        ArtistProfile,
        on_delete=models.CASCADE,
        related_name="profession_profiles",
    )
    profession = models.CharField(max_length=40, choices=ArtistProfile.PROFESSION_CHOICES)
    display_title = models.CharField(max_length=120, blank=True)
    tagline = models.CharField(max_length=160, blank=True)
    bio = models.TextField(blank=True)
    style = models.CharField(max_length=120, blank=True)
    cover_image = models.ImageField(upload_to="artist_profession_covers/", blank=True, null=True)
    visitor_banner = models.FileField(upload_to="artist_visitor_banners/", blank=True, null=True)
    visitor_banner_duration_seconds = models.PositiveSmallIntegerField(
        choices=VISITOR_BANNER_DURATION_CHOICES,
        default=30,
    )

    class Meta:
        unique_together = ("artist_profile", "profession")
        ordering = ["profession"]

    def __str__(self):
        return f"{self.artist_profile.stage_name} - {ArtistProfile.profession_label(self.profession)}"
