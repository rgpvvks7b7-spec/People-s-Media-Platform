from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from marketplace.models import Product
from notifications.models import Notification
from subscriptions.models import FanSubscription, OneTimeTip

from .models import ArtistFanContact, ArtistFollow, ArtistProfile, FanJourneyEvent

User = get_user_model()


class FanCrmTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.artist = User.objects.create_user(
            username="crm_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="CRM Artist")
        self.supporter = User.objects.create_user(
            username="crm_supporter",
            password="password123",
            user_type=User.FAN,
            email="supporter@example.com",
            discovery_location="Melbourne",
        )
        self.follower = User.objects.create_user(
            username="crm_follower",
            password="password123",
            user_type=User.FAN,
        )

        FanSubscription.objects.create(
            fan=self.supporter,
            artist=self.artist,
            monthly_amount="5.00",
            active=True,
        )
        ArtistFollow.objects.create(fan=self.supporter, artist=self.artist)
        ArtistFollow.objects.create(fan=self.follower, artist=self.artist)
        OneTimeTip.objects.create(fan=self.supporter, artist=self.artist, amount="10.00")
        FanJourneyEvent.objects.create(
            fan=self.supporter,
            artist=self.artist,
            event_type=FanJourneyEvent.PURCHASE,
            metadata={"amount": "12.00", "product_type": Product.EVENT_TICKET},
            occurred_at=timezone.now(),
        )
        contact = ArtistFanContact.objects.create(fan=self.supporter, artist=self.artist)
        contact.share(source=ArtistFanContact.SUPPORT_PROMPT)
        contact.save()

    def test_fan_list_requires_artist_account(self):
        response = self.client.get("/api/artists/fans/")
        self.assertEqual(response.status_code, 401)

        self.client.force_authenticate(self.supporter)
        response = self.client.get("/api/artists/fans/")
        self.assertEqual(response.status_code, 403)

    def test_fan_list_merges_relationships_into_one_row(self):
        self.client.force_authenticate(self.artist)
        response = self.client.get("/api/artists/fans/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["counts"]["supporters"], 1)
        self.assertEqual(response.data["counts"]["followers"], 2)
        self.assertEqual(response.data["counts"]["ticket_buyers"], 1)
        self.assertEqual(response.data["counts"]["mailing_list"], 1)

        top = response.data["results"][0]
        self.assertEqual(top["fan_username"], "crm_supporter")
        self.assertTrue(top["is_supporter"])
        self.assertEqual(top["monthly_amount"], "5.00")
        self.assertEqual(top["tips_total"], "10.00")
        self.assertEqual(top["purchases_total"], "12.00")
        self.assertEqual(top["lifetime_spend"], "22.00")
        self.assertTrue(top["is_ticket_buyer"])
        self.assertTrue(top["email_shared"])
        self.assertIn("supporters", top["segments"])
        self.assertIn("ticket_buyers", top["segments"])

    def test_fan_list_segment_filter(self):
        self.client.force_authenticate(self.artist)
        response = self.client.get("/api/artists/fans/?segment=ticket_buyers")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["fan_username"], "crm_supporter")

        bad = self.client.get("/api/artists/fans/?segment=nonsense")
        self.assertEqual(bad.status_code, 400)

    def test_broadcast_targets_segment_and_enforces_cooldown(self):
        self.client.force_authenticate(self.artist)
        response = self.client.post("/api/artists/fans/broadcast/", {
            "title": "New single Friday",
            "body": "Supporters hear it first at 9am.",
            "segment": "supporters",
        }, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["sent"], 1)
        note = Notification.objects.get(recipient=self.supporter, notification_type=Notification.MESSAGE)
        self.assertEqual(note.actor, self.artist)
        self.assertEqual(note.title, "New single Friday")
        self.assertFalse(
            Notification.objects.filter(recipient=self.follower, notification_type=Notification.MESSAGE).exists()
        )

        second = self.client.post("/api/artists/fans/broadcast/", {
            "title": "Another one",
            "body": "Too soon.",
            "segment": "all",
        }, format="json")
        self.assertEqual(second.status_code, 429)
        self.assertIn("next_allowed_at", second.data)

    def test_broadcast_to_all_reaches_followers(self):
        self.client.force_authenticate(self.artist)
        response = self.client.post("/api/artists/fans/broadcast/", {
            "title": "Show announced",
            "body": "Tickets on sale now.",
        }, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["sent"], 2)
        self.assertTrue(
            Notification.objects.filter(recipient=self.follower, notification_type=Notification.MESSAGE).exists()
        )

    def test_broadcast_validation(self):
        self.client.force_authenticate(self.artist)
        missing_title = self.client.post("/api/artists/fans/broadcast/", {"body": "hi"}, format="json")
        self.assertEqual(missing_title.status_code, 400)

        missing_body = self.client.post("/api/artists/fans/broadcast/", {"title": "hi"}, format="json")
        self.assertEqual(missing_body.status_code, 400)

        bad_segment = self.client.post("/api/artists/fans/broadcast/", {
            "title": "hi",
            "body": "there",
            "segment": "everyone",
        }, format="json")
        self.assertEqual(bad_segment.status_code, 400)
