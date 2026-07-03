from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from config.platform_fees import (
    CAMPAIGN_COOLDOWN_DAYS,
    CAMPAIGN_MAX_ACTIVE,
    CAMPAIGN_MAX_BUDGET,
    CAMPAIGN_MIN_BUDGET,
)


def normalize_genre_terms(value):
    """Split free-text genre/influence strings into a set of lowercase terms.

    Mirrors discovery.views.split_terms so campaign targeting matches the same
    vocabulary used by the recommendation engine.
    """
    return {
        term.strip().lower()
        for chunk in (value or "").replace("/", ",").split(",")
        for term in chunk.split()
        if term.strip()
    }


class Genre(models.Model):
    """Lightweight normalized genre registry used to power targeting UI.

    Free-text genres elsewhere (User.favorite_genres, ArtistProfile.genre,
    MusicUpload.genre) are matched against campaign targeting via shared
    term-normalization, so we get credible targeting without a risky
    cross-app schema migration.
    """

    slug = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=80)
    aliases = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def alias_terms(self):
        terms = normalize_genre_terms(self.aliases)
        terms.update(normalize_genre_terms(self.name))
        terms.add(self.slug.replace("-", " "))
        return {term for term in terms if term}


class PromotionLedgerEntry(models.Model):
    """Immutable wallet ledger. Every credit movement settles through here:
    artist credit purchases, plan grants, campaign spend, fan rewards, refunds.
    One ledger, no special cases.
    """

    PURCHASE = "purchase"  # artist bought credits (+)
    GRANT = "grant"  # plan-included credits (+)
    SPEND = "spend"  # campaign engagement charge (-)
    REWARD = "reward"  # fan earned discovery credit (+)
    REFUND = "refund"  # unused campaign budget returned (+)
    REDEEM = "redeem"  # credit spent/cashed out (-)

    ENTRY_TYPES = [
        (PURCHASE, "Credit purchase"),
        (GRANT, "Plan grant"),
        (SPEND, "Campaign spend"),
        (REWARD, "Discovery reward"),
        (REFUND, "Campaign refund"),
        (REDEEM, "Credit redeemed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="promotion_ledger_entries",
    )
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES)
    # Signed amount: positive adds credit, negative debits.
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    campaign = models.ForeignKey(
        "promotions.Campaign",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="ledger_entries",
    )
    description = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} {self.entry_type} {self.amount}"


class Campaign(models.Model):
    """A promoted release. The artist's budget is a ceiling (never a rank);
    reach is earned by fan engagement and capped hard at CAMPAIGN_MAX_BUDGET.
    """

    TRACK = "track"
    POST = "post"
    PRODUCT = "product"
    PROFILE = "profile"
    LIVESTREAM = "livestream"

    TARGET_TYPES = [
        (TRACK, "Track"),
        (POST, "Post"),
        (PRODUCT, "Merch / product"),
        (PROFILE, "Artist profile"),
        (LIVESTREAM, "Live stream"),
    ]

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    STATUSES = [
        (DRAFT, "Draft (awaiting payment)"),
        (ACTIVE, "Active"),
        (PAUSED, "Paused"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
    ]

    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="promotion_campaigns",
    )
    target_type = models.CharField(max_length=20, choices=TARGET_TYPES, default=TRACK)
    target_id = models.PositiveIntegerField()
    title = models.CharField(max_length=180, blank=True, default="")

    budget = models.DecimalField(max_digits=8, decimal_places=2, default=CAMPAIGN_MIN_BUDGET)
    spent = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=STATUSES, default=DRAFT)

    # Targeting. Genres stored as normalized space/comma terms.
    target_genres = models.CharField(max_length=255, blank=True, default="")
    target_location = models.CharField(max_length=120, blank=True, default="")
    target_artist_ids = models.CharField(max_length=255, blank=True, default="")

    discovery_score = models.FloatField(default=0.0)

    payment_provider = models.CharField(max_length=40, blank=True, default="")
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    cooldown_until = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "target_type", "target_id"]),
            models.Index(fields=["artist", "status"]),
        ]

    def __str__(self):
        return f"{self.artist_id} {self.target_type}#{self.target_id} ({self.status})"

    def save(self, *args, **kwargs):
        self.budget = Decimal(str(self.budget))
        # Enforce the hard cap at the data layer, not just the UI.
        if self.budget > CAMPAIGN_MAX_BUDGET:
            self.budget = CAMPAIGN_MAX_BUDGET
        if self.budget < CAMPAIGN_MIN_BUDGET:
            self.budget = CAMPAIGN_MIN_BUDGET
        super().save(*args, **kwargs)

    @property
    def remaining_budget(self):
        return max(self.budget - self.spent, Decimal("0.00"))

    @property
    def is_billable(self):
        return self.status == self.ACTIVE and self.remaining_budget > Decimal("0.00")

    def target_genre_terms(self):
        return normalize_genre_terms(self.target_genres)

    def target_artist_id_list(self):
        return [int(x) for x in self.target_artist_ids.split(",") if x.strip().isdigit()]

    @classmethod
    def active_for_artist(cls, artist):
        return cls.objects.filter(artist=artist, status=cls.ACTIVE)

    @classmethod
    def can_launch(cls, artist, now=None):
        """Returns (ok, reason). Encodes the anti-domination invariants:
        max simultaneous active campaigns + cooldown between campaigns.
        """
        now = now or timezone.now()
        active_count = cls.active_for_artist(artist).count()
        if active_count >= CAMPAIGN_MAX_ACTIVE:
            return False, (
                f"You already have {CAMPAIGN_MAX_ACTIVE} active campaigns. "
                "Wait for one to finish before launching another."
            )
        cooling = cls.objects.filter(
            artist=artist,
            cooldown_until__gt=now,
        ).order_by("-cooldown_until").first()
        if cooling:
            return False, (
                f"New campaigns are on a short cooldown until "
                f"{cooling.cooldown_until.date()}."
            )
        return True, ""


class CampaignEvent(models.Model):
    """Per-fan engagement with a promoted item. Powers both billing (charge)
    and the discovery score. Impressions are logged at charge=0.
    """

    IMPRESSION = "impression"
    FULL_LISTEN = "full_listen"
    SAVE = "save"
    FOLLOW = "follow"
    SHARE = "share"
    PURCHASE = "purchase"
    FEEDBACK_UP = "feedback_up"
    FEEDBACK_DOWN = "feedback_down"

    EVENT_TYPES = [
        (IMPRESSION, "Impression"),
        (FULL_LISTEN, "Full listen"),
        (SAVE, "Save"),
        (FOLLOW, "Follow"),
        (SHARE, "Share"),
        (PURCHASE, "Purchase"),
        (FEEDBACK_UP, "Would listen again"),
        (FEEDBACK_DOWN, "Not for me"),
    ]

    # Engagement types that count toward the discovery score (positive signal).
    POSITIVE_TYPES = {FULL_LISTEN, SAVE, FOLLOW, SHARE, PURCHASE, FEEDBACK_UP}

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="events")
    fan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="campaign_events",
    )
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    charge = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["campaign", "event_type"]),
            models.Index(fields=["campaign", "fan", "event_type"]),
        ]

    def __str__(self):
        return f"{self.campaign_id} {self.event_type} {self.charge}"
