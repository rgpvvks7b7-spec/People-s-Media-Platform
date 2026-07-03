from django.contrib.auth.models import AbstractUser
from django.db import models

from artists.themes import DEFAULT_THEME, THEME_CHOICES

class User(AbstractUser):
    FAN = 'fan'
    ARTIST = 'artist'
    HOST = 'host'
    ADMIN = 'admin'
    USER_TYPES = [(FAN, 'Fan'), (ARTIST, 'Artist'), (HOST, 'Host'), (ADMIN, 'Admin')]

    user_type = models.CharField(max_length=20, choices=USER_TYPES, default=FAN)
    display_name = models.CharField(max_length=80, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='covers/', blank=True, null=True)
    subscription_limit = models.PositiveIntegerField(default=50)
    favorite_genres = models.CharField(max_length=255, blank=True)
    discovery_location = models.CharField(max_length=120, blank=True)
    is_beta_tester = models.BooleanField(default=False)
    beta_notes = models.TextField(blank=True)
    artist_plan = models.CharField(max_length=40, default="free")
    share_email_with_supported_artists = models.BooleanField(default=False)
    email_share_consent_at = models.DateTimeField(blank=True, null=True)
    discovery_prefer_emerging = models.BooleanField(default=False)
    discovery_fewer_promoted = models.BooleanField(default=False)
    discovery_promoted_genres_only = models.BooleanField(default=False)
    stripe_artist_customer_id = models.CharField(max_length=255, blank=True, default="")
    stripe_artist_subscription_id = models.CharField(max_length=255, blank=True, default="")
    email_verified = models.BooleanField(default=True)
    email_verification_token = models.CharField(max_length=64, blank=True, default="")
    email_verification_sent_at = models.DateTimeField(blank=True, null=True)
    terms_accepted_at = models.DateTimeField(blank=True, null=True)
    session_login_count = models.PositiveIntegerField(default=0)
    theme_name = models.CharField(max_length=40, choices=THEME_CHOICES, default=DEFAULT_THEME)

    def __str__(self):
        return self.display_name or self.username


class BetaFeedback(models.Model):
    SETUP = "setup"
    NAVIGATION = "navigation"
    CONTENT = "content"
    PAYMENTS = "payments"
    OTHER = "other"

    CATEGORIES = [
        (SETUP, "Account setup"),
        (NAVIGATION, "Navigation"),
        (CONTENT, "Content and posting"),
        (PAYMENTS, "Payments and support"),
        (OTHER, "Other"),
    ]

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKER = "blocker"

    SEVERITIES = [
        (LOW, "Low"),
        (MEDIUM, "Medium"),
        (HIGH, "High"),
        (BLOCKER, "Blocker"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="beta_feedback")
    category = models.CharField(max_length=40, choices=CATEGORIES, default=NAVIGATION)
    severity = models.CharField(max_length=40, choices=SEVERITIES, default=MEDIUM)
    path = models.CharField(max_length=255, blank=True)
    summary = models.CharField(max_length=180)
    details = models.TextField(blank=True)
    user_agent = models.TextField(blank=True)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}: {self.summary}"


class FanWaitlistEntry(models.Model):
    email = models.EmailField(unique=True)
    city = models.CharField(max_length=120, blank=True)
    favorite_genres = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=40, default="prelaunch")
    confirmed = models.BooleanField(default=False)
    confirmation_token = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
