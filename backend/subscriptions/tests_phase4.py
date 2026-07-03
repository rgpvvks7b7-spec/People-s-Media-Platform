from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from artists.models import ArtistProfile
from notifications.models import Notification
from subscriptions.models import FanSubscription
from subscriptions.views import handle_invoice_payment_failed, update_subscription_status


User = get_user_model()


class StripeWebhookRecoveryTests(APITestCase):
    def setUp(self):
        self.fan = User.objects.create_user(
            username="billing_fan",
            password="password123",
            user_type=User.FAN,
        )
        self.artist = User.objects.create_user(
            username="billing_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Billing Artist")
        self.subscription = FanSubscription.objects.create(
            fan=self.fan,
            artist=self.artist,
            active=True,
            payment_provider="stripe",
            stripe_subscription_id="sub_test_123",
            stripe_status="active",
            monthly_amount="5.00",
        )

    def test_invoice_payment_failed_notifies_fan_and_artist(self):
        handle_invoice_payment_failed({"subscription": "sub_test_123"})

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.stripe_status, "past_due")
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.fan,
                title="Payment failed — update billing",
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.artist,
                title=f"Supporter payment failed ({self.fan.username})",
            ).exists()
        )

    def test_subscription_past_due_deactivates_and_notifies_once(self):
        update_subscription_status({"id": "sub_test_123", "status": "past_due"})

        self.subscription.refresh_from_db()
        self.assertFalse(self.subscription.active)
        self.assertEqual(self.subscription.stripe_status, "past_due")
        self.assertEqual(
            Notification.objects.filter(recipient=self.fan, title="Payment failed — update billing").count(),
            1,
        )
