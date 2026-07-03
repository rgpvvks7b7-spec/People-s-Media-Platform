from decimal import Decimal
from django.conf import settings
from django.db import models
from artists.models import ArtistProfile
from config.platform_fees import SUPPORT_PLATFORM_RATE, TIP_PLATFORM_RATE, split_amount


class SupportTier(models.Model):
    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_tiers")
    profession = models.CharField(
        max_length=40,
        choices=ArtistProfile.PROFESSION_CHOICES,
        default=ArtistProfile.DEFAULT_PROFESSION,
    )
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    monthly_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("1.00"))
    benefits = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["monthly_amount", "created_at"]

    def save(self, *args, **kwargs):
        self.monthly_amount = Decimal(str(self.monthly_amount))
        if self.monthly_amount < Decimal("1.00"):
            self.monthly_amount = Decimal("1.00")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.artist} {self.name} - ${self.monthly_amount}/month"


class FanSubscription(models.Model):
    fan = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="fan_subscriptions")
    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="artist_subscribers")
    tier = models.ForeignKey(SupportTier, on_delete=models.SET_NULL, blank=True, null=True, related_name="subscriptions")
    profession = models.CharField(
        max_length=40,
        choices=ArtistProfile.PROFESSION_CHOICES,
        default=ArtistProfile.DEFAULT_PROFESSION,
    )

    monthly_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("1.00"))
    artist_share = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.90"))
    platform_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.10"))

    billing_date = models.PositiveSmallIntegerField(default=1)
    active = models.BooleanField(default=True)
    payment_provider = models.CharField(max_length=40, blank=True, default="")
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, default="")
    stripe_customer_id = models.CharField(max_length=255, blank=True, default="")
    stripe_subscription_id = models.CharField(max_length=255, blank=True, default="")
    stripe_status = models.CharField(max_length=80, blank=True, default="")
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("fan", "artist", "profession")

    def save(self, *args, **kwargs):
        self.monthly_amount = Decimal(str(self.monthly_amount))

        if self.monthly_amount < Decimal("1.00"):
            self.monthly_amount = Decimal("1.00")

        self.artist_share, self.platform_fee = split_amount(self.monthly_amount, SUPPORT_PLATFORM_RATE)

        super().save(*args, **kwargs)

    def __str__(self):
        label = ArtistProfile.profession_label(self.profession)
        return f"{self.fan} supports {self.artist} ({label}) - ${self.monthly_amount}/month"


class OneTimeTip(models.Model):
    fan = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tips_sent")
    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tips_received")
    profession = models.CharField(
        max_length=40,
        choices=ArtistProfile.PROFESSION_CHOICES,
        default=ArtistProfile.DEFAULT_PROFESSION,
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    artist_share = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    platform_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    message = models.CharField(max_length=240, blank=True)
    is_public = models.BooleanField(default=True)
    payment_provider = models.CharField(max_length=40, blank=True, default="demo")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.amount = Decimal(str(self.amount))
        if self.amount < Decimal("1.00"):
            self.amount = Decimal("1.00")

        self.artist_share, self.platform_fee = split_amount(self.amount, TIP_PLATFORM_RATE)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.fan} tipped {self.artist} ${self.amount}"
