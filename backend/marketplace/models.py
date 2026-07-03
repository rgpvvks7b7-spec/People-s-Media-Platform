from django.conf import settings
from django.db import models
from artists.models import ArtistProfile
from config.platform_fees import (
    COMMISSION_PLATFORM_RATE,
    MARKETPLACE_PLATFORM_RATE,
    split_amount,
    split_ticket_sale,
)

class Product(models.Model):
    MERCH = "merch"
    MEMBERSHIP_MERCH = "membership_merch"
    DIGITAL_DOWNLOAD = "digital_download"
    EXTERNAL_FULFILLMENT = "external_fulfillment"
    GELATO_POD = "gelato_pod"
    SHOPIFY_STORE = "shopify_store"
    PRINTIFY_POD = "printify_pod"
    FOURTHWALL_STORE = "fourthwall_store"
    BANDCAMP_STORE = "bandcamp_store"
    PRINTFUL_POD = "printful_pod"
    VINYL = "vinyl"
    CASSETTE = "cassette"
    BEAT = "beat"
    SAMPLE_PACK = "sample_pack"
    ACAPELLA = "acapella"
    STEMS = "stems"
    MIDI_PACK = "midi_pack"
    DRUM_KIT = "drum_kit"
    PRESET_PACK = "preset_pack"
    EVENT_TICKET = "event_ticket"

    PRODUCT_TYPES = [
        (MERCH, "Merch"),
        (MEMBERSHIP_MERCH, "Membership Merch"),
        (DIGITAL_DOWNLOAD, "Digital Download"),
        (EXTERNAL_FULFILLMENT, "External Fulfillment"),
        (GELATO_POD, "Gelato Print-on-Demand"),
        (SHOPIFY_STORE, "Shopify Store"),
        (PRINTIFY_POD, "Printify Print-on-Demand"),
        (FOURTHWALL_STORE, "Fourthwall Store"),
        (BANDCAMP_STORE, "Bandcamp Store"),
        (PRINTFUL_POD, "Printful Print-on-Demand"),
        (VINYL, "Vinyl"),
        (CASSETTE, "Cassette"),
        (BEAT, "Beat"),
        (SAMPLE_PACK, "Sample Pack"),
        (ACAPELLA, "Acapella"),
        (STEMS, "Stems"),
        (MIDI_PACK, "MIDI Pack"),
        (DRUM_KIT, "Drum Kit"),
        (PRESET_PACK, "Preset Pack"),
        (EVENT_TICKET, "Event Ticket"),
    ]

    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products")
    profession = models.CharField(
        max_length=40,
        choices=ArtistProfile.PROFESSION_CHOICES,
        default=ArtistProfile.DEFAULT_PROFESSION,
    )
    product_type = models.CharField(max_length=40, choices=PRODUCT_TYPES, default=MERCH)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=1.00)
    artist_share = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    platform_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    host_share = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    image = models.ImageField(upload_to="marketplace/images/", blank=True, null=True)
    preview_audio = models.FileField(upload_to="marketplace/previews/", blank=True, null=True)
    product_file = models.FileField(upload_to="marketplace/files/", blank=True, null=True)
    external_url = models.URLField(blank=True)
    external_discount_code = models.CharField(max_length=80, blank=True)

    stock_quantity = models.PositiveIntegerField(default=0)
    sizes = models.CharField(max_length=255, blank=True, help_text="Example: S,M,L,XL")
    shipping_required = models.BooleanField(default=False)
    eligibility_months = models.PositiveIntegerField(default=0)
    fulfillment_status = models.CharField(max_length=40, default="not_started")
    fulfillment_notes = models.TextField(blank=True)
    is_supporter_only = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    bpm = models.PositiveIntegerField(blank=True, null=True)
    music_key = models.CharField(max_length=40, blank=True)
    license_type = models.CharField(max_length=80, blank=True, help_text="Non-exclusive, Exclusive, Royalty-free, etc")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.product_type}"

    def save(self, *args, **kwargs):
        if self.product_type == self.EVENT_TICKET:
            listing = None
            if self.pk:
                booking = self.space_bookings.select_related("listing").first()
                if booking:
                    listing = booking.listing
            artist_share, platform_fee, host_share = split_ticket_sale(self.price, listing)
            self.artist_share = artist_share
            self.platform_fee = platform_fee
            self.host_share = host_share
        else:
            self.artist_share, self.platform_fee = split_amount(self.price, MARKETPLACE_PLATFORM_RATE)
            self.host_share = 0
        super().save(*args, **kwargs)


class CommissionRequest(models.Model):
    NEW = "new"
    REVIEWING = "reviewing"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    COMPLETED = "completed"

    STATUSES = [
        (NEW, "New"),
        (REVIEWING, "Reviewing"),
        (ACCEPTED, "Accepted"),
        (DECLINED, "Declined"),
        (COMPLETED, "Completed"),
    ]

    fan = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="commission_requests")
    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="commission_inquiries")
    profession = models.CharField(
        max_length=40,
        choices=ArtistProfile.PROFESSION_CHOICES,
        default=ArtistProfile.VISUAL_ART,
    )
    title = models.CharField(max_length=160)
    brief = models.TextField()
    budget = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    deadline = models.DateField(blank=True, null=True)
    size_format = models.CharField(max_length=120, blank=True)
    reference_notes = models.TextField(blank=True)
    reference_links = models.TextField(blank=True)
    delivery_notes = models.TextField(blank=True)
    shipping_required = models.BooleanField(default=False)
    status = models.CharField(max_length=40, choices=STATUSES, default=NEW)
    artist_response = models.TextField(blank=True)
    quoted_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    quoted_artist_share = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    quoted_platform_fee = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title} for {self.artist}"

    def save(self, *args, **kwargs):
        if self.quoted_price is not None:
            self.quoted_artist_share, self.quoted_platform_fee = split_amount(
                self.quoted_price,
                COMMISSION_PLATFORM_RATE,
            )
        super().save(*args, **kwargs)
