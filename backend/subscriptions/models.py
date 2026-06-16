from decimal import Decimal
from django.conf import settings
from django.db import models

class FanSubscription(models.Model):
    fan = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="fan_subscriptions")
    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="artist_subscribers")

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
        unique_together = ("fan", "artist")

    def save(self, *args, **kwargs):
        self.monthly_amount = Decimal(str(self.monthly_amount))

        if self.monthly_amount < Decimal("1.00"):
            self.monthly_amount = Decimal("1.00")

        self.artist_share = self.monthly_amount * Decimal("0.90")
        self.platform_fee = self.monthly_amount * Decimal("0.10")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.fan} supports {self.artist} - ${self.monthly_amount}/month"
