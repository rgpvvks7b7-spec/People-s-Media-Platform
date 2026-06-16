from django.conf import settings
from django.db import models

class ArtistSignal(models.Model):
    SAVE = "save"
    SKIP = "skip"
    MORE_LIKE_THIS = "more_like_this"

    SIGNAL_TYPES = [
        (SAVE, "Save"),
        (SKIP, "Skip"),
        (MORE_LIKE_THIS, "More Like This"),
    ]

    fan = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='discovery_signals')
    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_discovery_signals')
    signal_type = models.CharField(max_length=40, choices=SIGNAL_TYPES, default=SAVE)
    liked_genre = models.CharField(max_length=80, blank=True)
    weight = models.FloatField(default=1.0)
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("fan", "artist", "signal_type")

class DiscoveryRule(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField()
    similarity_weight = models.FloatField(default=0.7)
    uniqueness_weight = models.FloatField(default=0.3)
    active = models.BooleanField(default=True)
