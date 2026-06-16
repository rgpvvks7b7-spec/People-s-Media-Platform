from django.conf import settings
from django.db import models

class MusicUpload(models.Model):
    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='music_uploads')
    title = models.CharField(max_length=160)
    audio_file = models.FileField(upload_to='music/')
    cover_art = models.ImageField(upload_to='cover_art/', blank=True, null=True)
    genre = models.CharField(max_length=80, blank=True)
    bpm = models.PositiveIntegerField(blank=True, null=True)
    is_downloadable = models.BooleanField(default=False)
    is_subscriber_only = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
