from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    FAN = 'fan'
    ARTIST = 'artist'
    ADMIN = 'admin'
    USER_TYPES = [(FAN, 'Fan'), (ARTIST, 'Artist'), (ADMIN, 'Admin')]

    user_type = models.CharField(max_length=20, choices=USER_TYPES, default=FAN)
    display_name = models.CharField(max_length=80, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    subscription_limit = models.PositiveIntegerField(default=50)
    favorite_genres = models.CharField(max_length=255, blank=True)
    discovery_location = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return self.display_name or self.username
