from django.conf import settings
from django.db import models


class HostProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="host_profile")
    business_name = models.CharField(max_length=160)
    contact_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=80, blank=True)
    verified = models.BooleanField(default=False)
    pending_ticket_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stripe_connect_account_id = models.CharField(max_length=255, blank=True, default="")
    stripe_connect_onboarded_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.business_name


class SpaceListing(models.Model):
    DOOR_PERCENT = "door_percent"
    FLAT_FEE = "flat_fee"
    FB_ONLY = "fb_only"

    SPLIT_TYPES = [
        (DOOR_PERCENT, "Door percent"),
        (FLAT_FEE, "Flat fee"),
        (FB_ONLY, "F&B only"),
    ]

    REQUEST = "request"
    INSTANT_BOOK = "instant_book"

    BOOKING_MODES = [
        (REQUEST, "Request"),
        (INSTANT_BOOK, "Instant book"),
    ]

    DRAFT = "draft"
    LIVE = "live"

    STATUSES = [
        (DRAFT, "Draft"),
        (LIVE, "Live"),
    ]

    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="space_listings")
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    photos = models.JSONField(default=list, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=80, blank=True)
    capacity = models.PositiveSmallIntegerField(default=20)
    available_windows = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)
    bar_open = models.BooleanField(default=True)
    kitchen_open = models.BooleanField(default=False)
    kitchen_notes = models.CharField(max_length=255, blank=True)
    drink_minimum = models.CharField(max_length=120, blank=True)
    last_call = models.CharField(max_length=80, blank=True)
    split_type = models.CharField(max_length=20, choices=SPLIT_TYPES, default=DOOR_PERCENT)
    host_cut_percent = models.PositiveSmallIntegerField(default=20)
    flat_fee_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    booking_mode = models.CharField(max_length=20, choices=BOOKING_MODES, default=REQUEST)
    min_local_supporters = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUSES, default=DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["city", "status"]),
            models.Index(fields=["host", "status"]),
        ]

    def __str__(self):
        return self.name


class SpaceListingPhoto(models.Model):
    STAGE = "stage"
    AUDIENCE = "audience"
    ROOM_OVERVIEW = "room_overview"
    LOAD_IN = "load_in"
    OTHER = "other"

    PHOTO_TYPES = [
        (STAGE, "Stage / band setup"),
        (AUDIENCE, "Audience area"),
        (ROOM_OVERVIEW, "Room overview"),
        (LOAD_IN, "Load-in / access"),
        (OTHER, "Other"),
    ]

    listing = models.ForeignKey(SpaceListing, on_delete=models.CASCADE, related_name="gallery_photos")
    image = models.ImageField(upload_to="spaces/listings/")
    photo_type = models.CharField(max_length=40, choices=PHOTO_TYPES, default=ROOM_OVERVIEW)
    caption = models.CharField(max_length=180, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.listing.name}: {self.get_photo_type_display()}"


class SpaceBooking(models.Model):
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

    STATUSES = [
        (REQUESTED, "Requested"),
        (CONFIRMED, "Confirmed"),
        (CANCELLED, "Cancelled"),
        (COMPLETED, "Completed"),
    ]

    listing = models.ForeignKey(SpaceListing, on_delete=models.CASCADE, related_name="bookings")
    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="space_bookings")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    expected_audience = models.PositiveSmallIntegerField(default=0)
    pitch = models.TextField(blank=True)
    material_url = models.URLField(blank=True, max_length=500)
    material_credit = models.CharField(max_length=200, blank=True)
    ticket_price = models.DecimalField(max_digits=8, decimal_places=2, default=15.00)
    status = models.CharField(max_length=20, choices=STATUSES, default=REQUESTED)
    linked_event_id = models.PositiveIntegerField(blank=True, null=True)
    ticket_product = models.ForeignKey(
        "marketplace.Product",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="space_bookings",
    )
    ticket_inventory = models.PositiveIntegerField(
        default=0,
        help_text="0 uses venue capacity; set explicitly to cap ticket sales.",
    )
    check_in_token = models.CharField(max_length=64, blank=True)
    attendance_checked_in = models.PositiveSmallIntegerField(default=0)
    dismissed_by_host_at = models.DateTimeField(blank=True, null=True)
    dismissed_by_artist_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_at"]
        indexes = [
            models.Index(fields=["listing", "status"]),
            models.Index(fields=["artist", "status"]),
        ]

    def __str__(self):
        return f"{self.listing} booking for {self.artist}"


class ShowTicketAdmission(models.Model):
    booking = models.ForeignKey(SpaceBooking, on_delete=models.CASCADE, related_name="ticket_admissions")
    fan = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="show_ticket_admissions")
    product = models.ForeignKey("marketplace.Product", on_delete=models.CASCADE, related_name="show_admissions")
    door_code = models.CharField(max_length=12, blank=True, default="", db_index=True)
    host_verified_at = models.DateTimeField(blank=True, null=True)
    host_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="verified_door_admissions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("booking", "fan")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Admission for {self.fan_id} on booking {self.booking_id}"


class ShowTicketStub(models.Model):
    booking = models.ForeignKey(SpaceBooking, on_delete=models.CASCADE, related_name="ticket_stubs")
    stub_code = models.CharField(max_length=12, unique=True, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_ticket_stubs")
    redeemed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="redeemed_ticket_stubs",
    )
    redeemed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Stub {self.stub_code} for booking {self.booking_id}"


class ShowCheckIn(models.Model):
    booking = models.ForeignKey(SpaceBooking, on_delete=models.CASCADE, related_name="check_ins")
    fan = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="show_check_ins")
    checked_in_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("booking", "fan")
        ordering = ["-checked_in_at"]

    def __str__(self):
        return f"{self.fan} checked in to booking {self.booking_id}"


class SpaceBookingReview(models.Model):
    ARTIST = "artist"
    HOST = "host"
    SHOW = "show"

    REVIEWEE_TYPES = [
        (ARTIST, "Artist"),
        (HOST, "Host"),
        (SHOW, "Show"),
    ]

    booking = models.ForeignKey(SpaceBooking, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="space_reviews")
    reviewee_type = models.CharField(max_length=20, choices=REVIEWEE_TYPES)
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("booking", "reviewer", "reviewee_type")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reviewer} reviewed {self.reviewee_type} on {self.booking_id}"
