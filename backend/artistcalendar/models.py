from django.conf import settings
from django.db import models
from artists.models import ArtistProfile


class ArtistCalendarItem(models.Model):
    RELEASE = "release"
    LIVE = "live"
    GIG = "gig"
    POV = "pov"
    OTHER = "other"

    ITEM_TYPES = [
        (RELEASE, "Release"),
        (LIVE, "Live"),
        (GIG, "Gig"),
        (POV, "Point of View"),
        (OTHER, "Other"),
    ]

    PRIVATE = "private"
    SUPPORTERS = "supporters"
    PUBLIC = "public"

    VISIBILITY_CHOICES = [
        (PRIVATE, "Private"),
        (SUPPORTERS, "Supporters"),
        (PUBLIC, "Public"),
    ]

    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calendar_items")
    profession = models.CharField(
        max_length=40,
        choices=ArtistProfile.PROFESSION_CHOICES,
        default=ArtistProfile.DEFAULT_PROFESSION,
    )
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(blank=True, null=True)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default=OTHER)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default=PRIVATE)
    supporter_early_hours = models.PositiveSmallIntegerField(default=0)
    music_upload = models.ForeignKey(
        "mediahub.MusicUpload",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="calendar_items",
    )
    live_session = models.ForeignKey(
        "livehub.LiveSession",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="calendar_items",
    )
    space_booking = models.OneToOneField(
        "spaces.SpaceBooking",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="calendar_item",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at", "created_at"]
        indexes = [
            models.Index(fields=["artist", "starts_at"]),
            models.Index(fields=["visibility", "starts_at"]),
        ]

    def __str__(self):
        return self.title
