from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from artists.models import ArtistFanContact, ArtistProfile
from marketplace.models import CommissionRequest, Product
from notifications.models import Notification
from subscriptions.models import FanSubscription


User = get_user_model()


class MarketplaceAccessTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="artist",
            password="password123",
            user_type=User.ARTIST,
        )
        self.fan = User.objects.create_user(
            username="fan",
            password="password123",
            user_type=User.FAN,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Artist", professions="music,visual_art")
        self.product = Product.objects.create(
            artist=self.artist,
            profession="visual_art",
            product_type=Product.SAMPLE_PACK,
            title="Supporter Pack",
            price="5.00",
            is_supporter_only=True,
            preview_audio="marketplace/previews/preview.mp3",
            product_file="marketplace/files/pack.zip",
        )

    def get_product_payload(self):
        response = self.client.get("/api/marketplace/")
        self.assertEqual(response.status_code, 200)
        return next(product for product in response.data if product["id"] == self.product.id)

    def test_supporter_only_files_are_hidden_until_active_support(self):
        anonymous_payload = self.get_product_payload()

        FanSubscription.objects.create(fan=self.fan, artist=self.artist, profession="visual_art", active=True)
        self.client.force_authenticate(self.fan)
        supporter_payload = self.get_product_payload()

        self.assertFalse(anonymous_payload["can_access"])
        self.assertIsNone(anonymous_payload["preview_audio"])
        self.assertIsNone(anonymous_payload["product_file"])
        self.assertTrue(supporter_payload["can_access"])
        # Preview audio is served through the protected endpoint, never /media/.
        self.assertIn(f"/api/marketplace/files/{self.product.id}/preview/", supporter_payload["preview_audio"])
        self.assertNotIn("/media/marketplace/previews/preview.mp3", supporter_payload["preview_audio"])
        # The paid download copy requires a purchase, not just supporter access.
        self.assertIsNone(supporter_payload["product_file"])
        self.assertFalse(supporter_payload["can_download"])

    def test_inactive_subscription_does_not_unlock_supporter_only_files(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, profession="visual_art", active=False)
        self.client.force_authenticate(self.fan)

        payload = self.get_product_payload()

        self.assertFalse(payload["can_access"])
        self.assertIsNone(payload["preview_audio"])
        self.assertIsNone(payload["product_file"])

    def test_support_for_music_does_not_unlock_visual_art_product(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, profession="music", active=True)
        self.client.force_authenticate(self.fan)

        payload = self.get_product_payload()

        self.assertFalse(payload["can_access"])
        self.assertIsNone(payload["preview_audio"])
        self.assertIsNone(payload["product_file"])

    def test_fans_cannot_create_products_but_artists_can(self):
        ArtistFanContact.objects.create(
            fan=self.fan,
            artist=self.artist,
            email_shared=True,
            source=ArtistFanContact.SUPPORT_PROMPT,
        )
        self.client.force_authenticate(self.fan)
        fan_response = self.client.post(
            "/api/marketplace/create/",
            {"title": "Fan Product", "price": "2.00"},
            format="multipart",
        )

        self.client.force_authenticate(self.artist)
        artist_response = self.client.post(
            "/api/marketplace/create/",
            {"title": "Artist Product", "price": "2.00"},
            format="multipart",
        )

        self.assertEqual(fan_response.status_code, 403)
        self.assertEqual(artist_response.status_code, 201)
        self.assertTrue(Product.objects.filter(title="Artist Product", artist=self.artist).exists())
        product = Product.objects.get(title="Artist Product")
        self.assertEqual(str(product.artist_share), "1.70")
        self.assertEqual(str(product.platform_fee), "0.30")
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.fan,
                actor=self.artist,
                notification_type=Notification.STORE,
                title="New store drop: Artist Product",
            ).exists()
        )

    def test_artist_can_create_linked_store_with_discount_code(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/marketplace/create/",
            {
                "title": "Shopify Shirt",
                "product_type": Product.EXTERNAL_FULFILLMENT,
                "external_url": "https://artist-shop.example.com/products/shirt",
                "external_discount_code": "SUPPORTER10",
            },
            format="multipart",
        )

        product = Product.objects.get(title="Shopify Shirt")
        payload = next(item for item in self.client.get("/api/marketplace/").data if item["id"] == product.id)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(product.external_discount_code, "SUPPORTER10")
        self.assertEqual(payload["external_url"], "https://artist-shop.example.com/products/shirt")
        self.assertEqual(payload["external_discount_code"], "SUPPORTER10")


class CommissionRequestTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="artist",
            password="password123",
            user_type=User.ARTIST,
        )
        self.fan = User.objects.create_user(
            username="fan",
            password="password123",
            user_type=User.FAN,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Artist", professions="music,visual_art")

    def test_fan_can_request_visual_art_commission(self):
        self.client.force_authenticate(self.fan)

        response = self.client.post(
            "/api/marketplace/commissions/",
            {
                "artist_id": self.artist.id,
                "profession": "visual_art",
                "title": "Watercolour portrait",
                "brief": "A small portrait based on reference photos.",
                "budget": "120.00",
                "deadline": "2026-08-01",
                "size_format": "A4",
                "reference_notes": "Soft colours, similar to your blue studies.",
                "reference_links": "https://example.com/reference",
                "delivery_notes": "Ship to Melbourne.",
                "shipping_required": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        request = CommissionRequest.objects.get(title="Watercolour portrait")
        self.assertEqual(request.profession, "visual_art")
        self.assertEqual(str(request.budget), "120.00")
        self.assertTrue(request.shipping_required)

    def test_commission_request_rejects_music_profession(self):
        self.client.force_authenticate(self.fan)

        response = self.client.post(
            "/api/marketplace/commissions/",
            {
                "artist_id": self.artist.id,
                "profession": "music",
                "title": "Song request",
                "brief": "Please make a track.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Commission requests are for arts and creative services.")

    def test_artist_can_update_commission_status_and_quote(self):
        request = CommissionRequest.objects.create(
            fan=self.fan,
            artist=self.artist,
            profession="visual_art",
            title="Poster",
            brief="A poster commission.",
        )
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            f"/api/marketplace/commissions/{request.id}/update/",
            {
                "status": "accepted",
                "artist_response": "I can do this as an A3 print.",
                "quoted_price": "180.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        request.refresh_from_db()
        self.assertEqual(request.status, CommissionRequest.ACCEPTED)
        self.assertEqual(str(request.quoted_price), "180.00")
        self.assertEqual(str(request.quoted_artist_share), "153.00")
        self.assertEqual(str(request.quoted_platform_fee), "27.00")


@override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
class MarketplacePurchaseTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="seller",
            password="password123",
            user_type=User.ARTIST,
        )
        self.fan = User.objects.create_user(
            username="buyer",
            password="password123",
            user_type=User.FAN,
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Seller")
        self.product = Product.objects.create(
            artist=self.artist,
            title="Gig Ticket",
            product_type=Product.EVENT_TICKET,
            price="15.00",
        )
        FanSubscription.objects.create(
            fan=self.fan,
            artist=self.artist,
            active=True,
            monthly_amount="5.00",
        )

    def test_supporter_can_purchase_product_and_dashboard_tracks_sale(self):
        supporter_product = Product.objects.create(
            artist=self.artist,
            title="Supporter Pack",
            product_type=Product.SAMPLE_PACK,
            price="9.00",
            is_supporter_only=True,
        )

        self.client.force_authenticate(self.fan)
        blocked = self.client.post("/api/marketplace/purchase/", {
            "product_id": supporter_product.id,
        }, format="json")
        self.assertEqual(blocked.status_code, 201)

        public_purchase = self.client.post("/api/marketplace/purchase/", {
            "product_id": self.product.id,
        }, format="json")
        self.assertEqual(public_purchase.status_code, 201)

        self.client.force_authenticate(self.artist)
        dashboard = self.client.get("/api/artists/dashboard/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertTrue(dashboard.data["revenue"]["marketplace_tracking_ready"])
        self.assertEqual(dashboard.data["revenue"]["marketplace_sales_this_month"]["amount"], "24.00")

    def test_duplicate_event_ticket_purchase_blocked(self):
        self.client.force_authenticate(self.fan)
        first = self.client.post("/api/marketplace/purchase/", {
            "product_id": self.product.id,
        }, format="json")
        self.assertEqual(first.status_code, 201)

        duplicate = self.client.post("/api/marketplace/purchase/", {
            "product_id": self.product.id,
        }, format="json")
        self.assertEqual(duplicate.status_code, 409)
        self.assertTrue(duplicate.data["already_purchased"])

    def test_my_purchases_lists_event_tickets(self):
        from spaces.models import HostProfile, SpaceBooking, SpaceListing

        host = User.objects.create_user(username="host", password="password123", user_type=User.HOST)
        HostProfile.objects.create(user=host, business_name="Venue", city="Melbourne")
        listing = SpaceListing.objects.create(host=host, name="Main Room", city="Melbourne")
        SpaceBooking.objects.create(
            listing=listing,
            artist=self.artist,
            ticket_product=self.product,
            starts_at=timezone.now() + timedelta(days=2),
            ends_at=timezone.now() + timedelta(days=2, hours=2),
            status=SpaceBooking.CONFIRMED,
        )

        self.client.force_authenticate(self.fan)
        purchase = self.client.post("/api/marketplace/purchase/", {
            "product_id": self.product.id,
        }, format="json")
        self.assertEqual(purchase.status_code, 201)

        response = self.client.get("/api/marketplace/my-purchases/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["tickets"]), 1)
        ticket = response.data["tickets"][0]
        self.assertEqual(ticket["product_id"], self.product.id)
        self.assertEqual(ticket["product_title"], "Gig Ticket")
        self.assertEqual(ticket["show"]["venue_name"], "Main Room")

    def test_purchase_creates_notifications(self):
        from notifications.models import Notification

        self.client.force_authenticate(self.fan)
        response = self.client.post("/api/marketplace/checkout/", {
            "product_id": self.product.id,
        }, format="json")
        self.assertEqual(response.status_code, 201)

        fan_notes = Notification.objects.filter(recipient=self.fan, notification_type=Notification.PURCHASE)
        artist_notes = Notification.objects.filter(recipient=self.artist, notification_type=Notification.PURCHASE)
        self.assertEqual(fan_notes.count(), 1)
        self.assertEqual(artist_notes.count(), 1)

    def test_cart_checkout_purchases_multiple_items(self):
        merch = Product.objects.create(
            artist=self.artist,
            title="T-Shirt",
            product_type=Product.MERCH,
            price="15.00",
        )
        second = Product.objects.create(
            artist=self.artist,
            title="Sample Pack",
            product_type=Product.SAMPLE_PACK,
            price="8.00",
        )
        self.client.force_authenticate(self.fan)
        response = self.client.post("/api/marketplace/cart-checkout/", {
            "product_ids": [merch.id, second.id],
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["total"], "23.00")

    def test_my_purchases_splits_upcoming_and_attended_tickets(self):
        from spaces.models import HostProfile, ShowCheckIn, SpaceBooking, SpaceListing

        host = User.objects.create_user(username="host2", password="password123", user_type=User.HOST)
        HostProfile.objects.create(user=host, business_name="Room", city="Melbourne")
        listing = SpaceListing.objects.create(host=host, name="Back Room", city="Melbourne")
        past_product = Product.objects.create(
            artist=self.artist,
            title="Past Gig",
            product_type=Product.EVENT_TICKET,
            price="12.00",
        )
        upcoming = SpaceBooking.objects.create(
            listing=listing,
            artist=self.artist,
            ticket_product=self.product,
            starts_at=timezone.now() + timedelta(days=3),
            ends_at=timezone.now() + timedelta(days=3, hours=2),
            status=SpaceBooking.CONFIRMED,
        )
        attended = SpaceBooking.objects.create(
            listing=listing,
            artist=self.artist,
            ticket_product=past_product,
            starts_at=timezone.now() - timedelta(days=2),
            ends_at=timezone.now() - timedelta(days=2, hours=-2),
            status=SpaceBooking.COMPLETED,
        )

        self.client.force_authenticate(self.fan)
        first = self.client.post("/api/marketplace/purchase/", {"product_id": self.product.id}, format="json")
        second = self.client.post("/api/marketplace/purchase/", {"product_id": past_product.id}, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        ShowCheckIn.objects.create(booking=attended, fan=self.fan)

        response = self.client.get("/api/marketplace/my-purchases/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["upcoming_tickets"]), 1)
        self.assertEqual(len(response.data["attended_tickets"]), 1)
        self.assertEqual(response.data["upcoming_tickets"][0]["collection_status"], "upcoming")
        self.assertEqual(response.data["attended_tickets"][0]["collection_status"], "attended")
        self.assertEqual(response.data["attended_tickets"][0]["show"]["venue_name"], "Back Room")
        self.assertEqual(response.data["upcoming_tickets"][0]["show"]["booking_id"], upcoming.id)

