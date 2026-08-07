from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from artists.models import ArtistFanContact, ArtistFollow, ArtistProfile
from discovery.models import ArtistSignal
from notifications.models import Notification
from spaces.models import HostProfile, SpaceBooking, SpaceListing
from subscriptions.models import FanSubscription


User = get_user_model()


class GigNotificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.host = User.objects.create_user(username="host", password="pass", user_type=User.HOST)
        self.artist = User.objects.create_user(username="artist", password="pass", user_type=User.ARTIST)
        self.fan = User.objects.create_user(
            username="fan",
            password="pass",
            user_type=User.FAN,
            email="fan@example.com",
            discovery_location="Melbourne",
        )
        self.opted_in_fan = User.objects.create_user(
            username="opted_in",
            password="pass",
            user_type=User.FAN,
            email="opted@example.com",
            discovery_location="Melbourne",
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Local Act", city="Melbourne")
        HostProfile.objects.create(user=self.host, business_name="North Bar", city="Melbourne")
        self.listing = SpaceListing.objects.create(
            host=self.host,
            name="Back Room",
            city="Melbourne",
            status=SpaceListing.LIVE,
        )
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, active=True, monthly_amount="3.00")
        FanSubscription.objects.create(fan=self.opted_in_fan, artist=self.artist, active=True, monthly_amount="5.00")
        contact = ArtistFanContact.objects.create(artist=self.artist, fan=self.opted_in_fan)
        contact.share(ArtistFanContact.SUPPORT_PROMPT)
        contact.save()

    def create_confirmed_booking(self):
        starts_at = timezone.now() + timedelta(days=4)
        return SpaceBooking.objects.create(
            listing=self.listing,
            artist=self.artist,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=2),
            status=SpaceBooking.CONFIRMED,
        )

    def test_notify_reaches_all_local_subscribers_not_only_email_opted_in(self):
        booking = self.create_confirmed_booking()
        self.client.force_authenticate(self.artist)
        response = self.client.post(f"/api/spaces/bookings/{booking.id}/notify-local-supporters/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["notified_count"], 2)
        self.assertTrue(Notification.objects.filter(recipient=self.fan, notification_type=Notification.GIG).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.opted_in_fan, notification_type=Notification.GIG).exists())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_email_only_sent_to_opted_in_supporters(self):
        booking = self.create_confirmed_booking()
        self.client.force_authenticate(self.artist)
        response = self.client.post(f"/api/spaces/bookings/{booking.id}/notify-local-supporters/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email_count"], 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["opted@example.com"])

    def test_confirming_booking_auto_notifies_local_subscribers(self):
        starts_at = timezone.now() + timedelta(days=6)
        booking = SpaceBooking.objects.create(
            listing=self.listing,
            artist=self.artist,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=2),
            status=SpaceBooking.REQUESTED,
        )

        self.client.force_authenticate(self.host)
        response = self.client.post(f"/api/spaces/bookings/{booking.id}/status/", {
            "status": SpaceBooking.CONFIRMED,
            "publish_to_calendar": True,
        }, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Notification.objects.filter(notification_type=Notification.GIG).count(), 2)

    def test_manual_reminder_respects_cooldown(self):
        booking = self.create_confirmed_booking()
        self.client.force_authenticate(self.artist)
        first = self.client.post(f"/api/spaces/bookings/{booking.id}/notify-local-supporters/")
        self.assertEqual(first.status_code, 200)
        second = self.client.post(f"/api/spaces/bookings/{booking.id}/notify-local-supporters/")
        self.assertEqual(second.status_code, 429)

    def test_notify_reaches_local_saved_fans_without_subscription(self):
        saver = User.objects.create_user(
            username="saver",
            password="pass",
            user_type=User.FAN,
            discovery_location="Melbourne",
        )
        ArtistSignal.objects.create(
            fan=saver,
            artist=self.artist,
            signal_type=ArtistSignal.SAVE,
            liked_genre="indie",
            weight=1.4,
        )
        ArtistFollow.objects.get_or_create(fan=saver, artist=self.artist)

        booking = self.create_confirmed_booking()
        self.client.force_authenticate(self.artist)
        response = self.client.post(f"/api/spaces/bookings/{booking.id}/notify-local-supporters/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["notified_count"], 3)
        self.assertTrue(
            Notification.objects.filter(recipient=saver, notification_type=Notification.GIG).exists()
        )

    def test_remote_saved_fan_is_not_notified(self):
        remote = User.objects.create_user(
            username="remote",
            password="pass",
            user_type=User.FAN,
            discovery_location="Sydney",
        )
        ArtistSignal.objects.create(
            fan=remote,
            artist=self.artist,
            signal_type=ArtistSignal.SAVE,
            liked_genre="indie",
            weight=1.4,
        )

        booking = self.create_confirmed_booking()
        self.client.force_authenticate(self.artist)
        response = self.client.post(f"/api/spaces/bookings/{booking.id}/notify-local-supporters/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["notified_count"], 2)
        self.assertFalse(
            Notification.objects.filter(recipient=remote, notification_type=Notification.GIG).exists()
        )
