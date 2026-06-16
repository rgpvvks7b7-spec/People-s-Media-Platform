from django.conf import settings
from django.db import models

class Product(models.Model):
    MERCH = "merch"
    BEAT = "beat"
    SAMPLE_PACK = "sample_pack"
    ACAPELLA = "acapella"
    STEMS = "stems"
    MIDI_PACK = "midi_pack"
    DRUM_KIT = "drum_kit"
    PRESET_PACK = "preset_pack"

    PRODUCT_TYPES = [
        (MERCH, "Merch"),
        (BEAT, "Beat"),
        (SAMPLE_PACK, "Sample Pack"),
        (ACAPELLA, "Acapella"),
        (STEMS, "Stems"),
        (MIDI_PACK, "MIDI Pack"),
        (DRUM_KIT, "Drum Kit"),
        (PRESET_PACK, "Preset Pack"),
    ]

    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products")
    product_type = models.CharField(max_length=40, choices=PRODUCT_TYPES, default=MERCH)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=1.00)

    image = models.ImageField(upload_to="marketplace/images/", blank=True, null=True)
    preview_audio = models.FileField(upload_to="marketplace/previews/", blank=True, null=True)
    product_file = models.FileField(upload_to="marketplace/files/", blank=True, null=True)

    stock_quantity = models.PositiveIntegerField(default=0)
    sizes = models.CharField(max_length=255, blank=True, help_text="Example: S,M,L,XL")
    shipping_required = models.BooleanField(default=False)
    is_supporter_only = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    bpm = models.PositiveIntegerField(blank=True, null=True)
    music_key = models.CharField(max_length=40, blank=True)
    license_type = models.CharField(max_length=80, blank=True, help_text="Non-exclusive, Exclusive, Royalty-free, etc")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.product_type}"
