from django.conf import settings
from django.db import models
from artists.models import ArtistProfile

class MusicUpload(models.Model):
    HUMAN_MADE = "human_made"
    AI_ASSISTED = "ai_assisted"
    AI_COLLABORATIVE = "ai_collaborative"
    AI_GENERATED = "ai_generated"

    AI_DISCLOSURE_CHOICES = [
        (HUMAN_MADE, "Human-made"),
        (AI_ASSISTED, "AI-assisted"),
        (AI_COLLABORATIVE, "AI-collaborative"),
        (AI_GENERATED, "Fully AI-generated"),
    ]

    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='music_uploads')
    profession = models.CharField(
        max_length=40,
        choices=ArtistProfile.PROFESSION_CHOICES,
        default=ArtistProfile.DEFAULT_PROFESSION,
    )
    title = models.CharField(max_length=160)
    audio_file = models.FileField(upload_to='music/')
    cover_art = models.ImageField(upload_to='cover_art/', blank=True, null=True)
    library_cover = models.ForeignKey(
        "SongCoverArt",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="tracks",
    )
    genre = models.CharField(max_length=80, blank=True)
    bpm = models.PositiveIntegerField(blank=True, null=True)
    is_downloadable = models.BooleanField(default=False)
    is_subscriber_only = models.BooleanField(default=True)
    preview_enabled = models.BooleanField(default=True)
    preview_seconds = models.PositiveSmallIntegerField(default=30)
    allow_fan_radio = models.BooleanField(default=False)
    ai_disclosure_level = models.CharField(
        max_length=40,
        choices=AI_DISCLOSURE_CHOICES,
        default=HUMAN_MADE,
    )
    ai_disclosure_note = models.TextField(blank=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def ai_disclosure_badge(self):
        if self.ai_disclosure_level == self.AI_ASSISTED:
            return "AI-assisted · disclosed"
        if self.ai_disclosure_level == self.AI_COLLABORATIVE:
            return "AI-collaborative · disclosed"
        return "Human-made"


class AiReviewFlag(models.Model):
    OPEN = "open"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"

    STATUS_CHOICES = [
        (OPEN, "Open"),
        (REVIEWED, "Reviewed"),
        (DISMISSED, "Dismissed"),
    ]

    upload = models.ForeignKey(MusicUpload, on_delete=models.CASCADE, related_name="ai_review_flags")
    reason = models.CharField(max_length=240)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.upload} AI review: {self.reason}"


class SongCoverArt(models.Model):
    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="song_cover_art",
    )
    profession = models.CharField(
        max_length=40,
        choices=ArtistProfile.PROFESSION_CHOICES,
        default=ArtistProfile.DEFAULT_PROFESSION,
    )
    image = models.ImageField(upload_to="cover_art/library/")
    label = models.CharField(max_length=120, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return self.label or f"Cover #{self.pk}"


class ArtworkUpload(models.Model):
    AVAILABLE = "available"
    SOLD = "sold"
    PRINT_ONLY = "print_only"
    NOT_FOR_SALE = "not_for_sale"

    AVAILABILITY_CHOICES = [
        (AVAILABLE, "Available"),
        (SOLD, "Sold"),
        (PRINT_ONLY, "Print only"),
        (NOT_FOR_SALE, "Not for sale"),
    ]

    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="artwork_uploads")
    profession = models.CharField(
        max_length=40,
        choices=ArtistProfile.PROFESSION_CHOICES,
        default=ArtistProfile.VISUAL_ART,
    )
    title = models.CharField(max_length=160)
    image = models.ImageField(upload_to="artworks/")
    description = models.TextField(blank=True)
    medium = models.CharField(max_length=120, blank=True)
    dimensions = models.CharField(max_length=80, blank=True)
    year = models.PositiveIntegerField(blank=True, null=True)
    availability = models.CharField(max_length=40, choices=AVAILABILITY_CHOICES, default=AVAILABLE)
    is_supporter_only = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class FanPlaylist(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="fan_playlists")
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class FanPlaylistTrack(models.Model):
    playlist = models.ForeignKey(FanPlaylist, on_delete=models.CASCADE, related_name="playlist_tracks")
    track = models.ForeignKey(MusicUpload, on_delete=models.CASCADE, related_name="playlist_entries")
    position = models.PositiveIntegerField(default=0)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "added_at"]
        unique_together = ("playlist", "track")
