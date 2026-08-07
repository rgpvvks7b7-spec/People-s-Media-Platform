from datetime import datetime, timedelta

from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from artists.models import ArtistFanContact, ArtistProfile
from notifications.models import Notification
from marketplace.models import Product
from subscriptions.models import FanSubscription
from .models import HostProfile, SpaceBooking, SpaceListing, SpaceListingPhoto


User = get_user_model()


class SpacesApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.host = User.objects.create_user(username="host", password="pass", user_type=User.HOST, display_name="North Bar")
        self.artist = User.objects.create_user(username="artist", password="pass", user_type=User.ARTIST, display_name="Local Act")
        self.fan = User.objects.create_user(
            username="fan",
            password="pass",
            user_type=User.FAN,
            email="fan@example.com",
            discovery_location="Melbourne",
        )
        self.artist_profile = ArtistProfile.objects.create(
            owner=self.artist,
            stage_name="Local Act",
            city="Melbourne",
            professions=ArtistProfile.MUSIC,
        )

    def create_live_listing(self, **overrides):
        HostProfile.objects.create(user=self.host, business_name="North Bar", city="Melbourne")
        payload = {
            "name": "Late room",
            "description": "Small room after dinner service.",
            "address": "1 High St",
            "city": "Melbourne",
            "capacity": 60,
            "available_windows": ["Tue after 21:00"],
            "tags": ["comedy_friendly", "acoustic"],
            "bar_open": True,
            "kitchen_open": True,
            "split_type": SpaceListing.DOOR_PERCENT,
            "host_cut_percent": 25,
            "booking_mode": SpaceListing.REQUEST,
            "status": SpaceListing.LIVE,
        }
        payload.update(overrides)
        self.client.force_authenticate(self.host)
        response = self.client.post("/api/spaces/listings/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        return SpaceListing.objects.get(id=response.data["listing"]["id"])

    def test_host_can_create_listing_and_public_browse_sees_live_spaces(self):
        listing = self.create_live_listing()
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/spaces/listings/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], listing.id)
        self.assertEqual(response.data["results"][0]["host_business_name"], "North Bar")

    def test_host_can_upload_space_photos_when_creating_listing(self):
        HostProfile.objects.create(user=self.host, business_name="North Bar", city="Melbourne")
        image_bytes = BytesIO()
        Image.new("RGB", (640, 480), color=(120, 80, 40)).save(image_bytes, format="JPEG")
        image_bytes.seek(0)
        stage_photo = SimpleUploadedFile("stage.jpg", image_bytes.read(), content_type="image/jpeg")
        image_bytes.seek(0)
        audience_photo = SimpleUploadedFile("audience.jpg", image_bytes.read(), content_type="image/jpeg")

        self.client.force_authenticate(self.host)
        response = self.client.post(
            "/api/spaces/listings/",
            {
                "name": "Photo room",
                "description": "Room with stage and seating photos.",
                "address": "2 Photo Lane",
                "city": "Melbourne",
                "capacity": 50,
                "available_windows": [{"day": "fri", "start": "19:00", "end": "23:00"}],
                "split_type": SpaceListing.DOOR_PERCENT,
                "booking_mode": SpaceListing.REQUEST,
                "status": SpaceListing.LIVE,
                "photos": [stage_photo, audience_photo],
                "photo_types": ["stage", "audience"],
                "photo_captions": ["Small corner stage", "Cafe seating for 50"],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        listing = SpaceListing.objects.get(id=response.data["listing"]["id"])
        self.assertEqual(listing.gallery_photos.count(), 2)
        self.assertEqual(response.data["listing"]["photos"][0]["photo_type"], "stage")
        self.assertTrue(response.data["listing"]["photos"][0]["url"].endswith(".jpg"))

        browse = self.client.get("/api/spaces/listings/")
        self.assertEqual(browse.status_code, 200)
        self.assertEqual(len(browse.data["results"][0]["photos"]), 2)

    def test_host_can_update_and_delete_own_listing(self):
        listing = self.create_live_listing()
        self.client.force_authenticate(self.host)

        update = self.client.patch(f"/api/spaces/listings/{listing.id}/", {
            "name": "Updated room",
            "city": "Melbourne",
            "capacity": 80,
            "split_type": SpaceListing.FLAT_FEE,
            "flat_fee_amount": "150.00",
            "booking_mode": SpaceListing.INSTANT_BOOK,
            "status": SpaceListing.LIVE,
        }, format="json")

        self.assertEqual(update.status_code, 200)
        listing.refresh_from_db()
        self.assertEqual(listing.name, "Updated room")
        self.assertEqual(listing.capacity, 80)
        self.assertEqual(listing.split_type, SpaceListing.FLAT_FEE)

        delete = self.client.delete(f"/api/spaces/listings/{listing.id}/")
        self.assertEqual(delete.status_code, 200)
        self.assertFalse(SpaceListing.objects.filter(id=listing.id).exists())

    def test_artist_requests_booking_and_host_confirms_with_fb_policy(self):
        listing = self.create_live_listing()
        starts_at = timezone.now() + timedelta(days=7)
        ends_at = starts_at + timedelta(hours=2)

        self.client.force_authenticate(self.artist)
        response = self.client.post("/api/spaces/bookings/", {
            "listing_id": listing.id,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "expected_audience": 40,
            "pitch": "Two sets and ticketed door.",
        }, format="json")

        self.assertEqual(response.status_code, 201)
        booking = SpaceBooking.objects.get(id=response.data["booking"]["id"])
        self.assertEqual(booking.status, SpaceBooking.REQUESTED)

        self.client.force_authenticate(self.host)
        confirm = self.client.post(f"/api/spaces/bookings/{booking.id}/status/", {
            "status": SpaceBooking.CONFIRMED,
        }, format="json")
        self.assertEqual(confirm.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.status, SpaceBooking.CONFIRMED)

        complete = self.client.post(f"/api/spaces/bookings/{booking.id}/status/", {
            "status": SpaceBooking.COMPLETED,
            "attendance_checked_in": 38,
        }, format="json")
        self.assertEqual(complete.status_code, 200)

        earnings = self.client.get("/api/spaces/host-earnings/")
        self.assertEqual(earnings.data["completed_bookings"], 1)
        self.assertEqual(earnings.data["attendance_checked_in"], 38)
        self.assertIn("F&B stays with the venue", earnings.data["policy"])
        self.assertIn("pending_ticket_earnings", earnings.data)
        self.assertIn("Ticket door share", earnings.data["ticket_share_note"])
        self.assertFalse(earnings.data["payouts_ready"])

    def test_draw_profile_returns_aggregates_without_fan_emails(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, active=True, monthly_amount="5.00")
        contact = ArtistFanContact.objects.create(artist=self.artist, fan=self.fan)
        contact.share(ArtistFanContact.SUPPORT_PROMPT)
        contact.save()
        listing = self.create_live_listing()
        SpaceBooking.objects.create(
            listing=listing,
            artist=self.artist,
            starts_at=timezone.now() - timedelta(days=10),
            ends_at=timezone.now() - timedelta(days=10, hours=-2),
            status=SpaceBooking.COMPLETED,
            attendance_checked_in=24,
        )

        self.client.force_authenticate(self.host)
        response = self.client.get(f"/api/spaces/artists/{self.artist.id}/draw-profile/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["local_supporters"], 1)
        self.assertEqual(response.data["notifyable_local_supporters_count"], 1)
        self.assertEqual(response.data["active_subscribers"], 1)
        self.assertEqual(response.data["past_gig_attendance"], 24)
        self.assertNotIn("email", response.data)

    def test_confirmed_booking_can_notify_local_opted_in_supporters(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, active=True, monthly_amount="5.00")
        contact = ArtistFanContact.objects.create(artist=self.artist, fan=self.fan)
        contact.share(ArtistFanContact.SUPPORT_PROMPT)
        contact.save()
        listing = self.create_live_listing()
        booking = SpaceBooking.objects.create(
            listing=listing,
            artist=self.artist,
            starts_at=timezone.now() + timedelta(days=5),
            ends_at=timezone.now() + timedelta(days=5, hours=2),
            status=SpaceBooking.CONFIRMED,
        )

        self.client.force_authenticate(self.artist)
        response = self.client.post(f"/api/spaces/bookings/{booking.id}/notify-local-supporters/")

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data["notified_count"], 1)
        self.assertTrue(Notification.objects.filter(recipient=self.fan, actor=self.artist, notification_type=Notification.GIG).exists())

    def test_confirmed_booking_notifies_subscriber_without_email_share(self):
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, active=True, monthly_amount="5.00")
        listing = self.create_live_listing()
        booking = SpaceBooking.objects.create(
            listing=listing,
            artist=self.artist,
            starts_at=timezone.now() + timedelta(days=5),
            ends_at=timezone.now() + timedelta(days=5, hours=2),
            status=SpaceBooking.CONFIRMED,
        )

        self.client.force_authenticate(self.artist)
        response = self.client.post(f"/api/spaces/bookings/{booking.id}/notify-local-supporters/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["notified_count"], 1)
        notification = Notification.objects.get(recipient=self.fan, notification_type=Notification.GIG)
        self.assertIn("my-scene", notification.target_url)
        self.assertIn(f"show={booking.id}", notification.target_url)

    def test_confirmed_booking_creates_public_calendar_item(self):
        listing = self.create_live_listing()
        starts_at = timezone.now() + timedelta(days=3)
        ends_at = starts_at + timedelta(hours=2)

        self.client.force_authenticate(self.artist)
        response = self.client.post("/api/spaces/bookings/", {
            "listing_id": listing.id,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "expected_audience": 30,
            "pitch": "Local supporters night.",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        booking = SpaceBooking.objects.get(id=response.data["booking"]["id"])

        self.client.force_authenticate(self.host)
        confirm = self.client.post(f"/api/spaces/bookings/{booking.id}/status/", {
            "status": SpaceBooking.CONFIRMED,
            "publish_to_calendar": True,
        }, format="json")
        self.assertEqual(confirm.status_code, 200)

        from artistcalendar.models import ArtistCalendarItem

        calendar_item = ArtistCalendarItem.objects.get(space_booking=booking)
        self.assertEqual(calendar_item.item_type, ArtistCalendarItem.GIG)
        self.assertEqual(calendar_item.visibility, ArtistCalendarItem.PUBLIC)
        self.assertIn("Live at", calendar_item.title)

    def test_completed_booking_reviews_and_challenge_progress(self):
        from challenges.models import ArtistChallengeProgress, ChallengeTemplate
        from challenges.services import ensure_default_templates

        ensure_default_templates()
        listing = self.create_live_listing(booking_mode=SpaceListing.INSTANT_BOOK)
        starts_at = timezone.now() + timedelta(days=2)
        ends_at = starts_at + timedelta(hours=2)

        self.client.force_authenticate(self.artist)
        create = self.client.post("/api/spaces/bookings/", {
            "listing_id": listing.id,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "publish_to_calendar": True,
        }, format="json")
        self.assertEqual(create.status_code, 201)
        booking = SpaceBooking.objects.get(id=create.data["booking"]["id"])
        self.assertEqual(booking.status, SpaceBooking.CONFIRMED)

        progress = ArtistChallengeProgress.objects.get(
            artist=self.artist,
            template__metric="spaces_booking",
        )
        self.assertGreaterEqual(progress.progress, 1)

        self.client.force_authenticate(self.host)
        complete = self.client.post(f"/api/spaces/bookings/{booking.id}/status/", {
            "status": SpaceBooking.COMPLETED,
            "attendance_checked_in": 42,
        }, format="json")
        self.assertEqual(complete.status_code, 200)

        self.client.force_authenticate(self.host)
        review = self.client.post(f"/api/spaces/bookings/{booking.id}/reviews/", {
            "reviewee_type": "artist",
            "rating": 5,
            "comment": "Great turnout and bar sales.",
        }, format="json")
        self.assertEqual(review.status_code, 201)

        self.client.force_authenticate(self.artist)
        host_review = self.client.post(f"/api/spaces/bookings/{booking.id}/reviews/", {
            "reviewee_type": "host",
            "rating": 4,
            "comment": "Good room.",
        }, format="json")
        self.assertEqual(host_review.status_code, 201)

    def test_draw_profile_uses_venue_city_when_provided(self):
        other_city_fan = User.objects.create_user(
            username="sydney_fan",
            password="pass",
            user_type=User.FAN,
            discovery_location="Sydney",
        )
        FanSubscription.objects.create(fan=other_city_fan, artist=self.artist, active=True, monthly_amount="5.00")
        FanSubscription.objects.create(fan=self.fan, artist=self.artist, active=True, monthly_amount="5.00")

        self.client.force_authenticate(self.host)
        response = self.client.get(
            f"/api/spaces/artists/{self.artist.id}/draw-profile/?venue_city=Melbourne"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["local_city"], "Melbourne")
        self.assertEqual(response.data["local_supporters"], 1)

    def test_booking_blocked_when_local_supporters_below_minimum(self):
        listing = self.create_live_listing(min_local_supporters=5)
        starts_at = timezone.now() + timedelta(days=5)
        ends_at = starts_at + timedelta(hours=2)

        self.client.force_authenticate(self.artist)
        response = self.client.post("/api/spaces/bookings/", {
            "listing_id": listing.id,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "expected_audience": 20,
            "pitch": "Need more local draw.",
        }, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("requires at least 5 local supporters", response.data["error"])

    def test_booking_must_match_host_availability_window(self):
        listing = self.create_live_listing(
            available_windows=[{"day": "fri", "start": "19:00", "end": "23:00"}],
        )
        self.client.force_authenticate(self.artist)

        starts_at = timezone.now() + timedelta(days=1)
        while starts_at.strftime("%a").lower() != "fri":
            starts_at += timedelta(days=1)
        starts_at = starts_at.replace(hour=20, minute=0, second=0, microsecond=0)
        if timezone.is_naive(starts_at):
            starts_at = timezone.make_aware(starts_at, timezone.get_current_timezone())
        ends_at = starts_at + timedelta(hours=2)

        ok = self.client.post("/api/spaces/bookings/", {
            "listing_id": listing.id,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "expected_audience": 30,
            "pitch": "Friday slot inside host hours.",
        }, format="json")
        self.assertEqual(ok.status_code, 201)

        wrong_day = starts_at + timedelta(days=1)
        if wrong_day.strftime("%a").lower() == "fri":
            wrong_day += timedelta(days=1)
        wrong_day = wrong_day.replace(hour=20, minute=0, second=0, microsecond=0)
        bad_day = self.client.post("/api/spaces/bookings/", {
            "listing_id": listing.id,
            "starts_at": wrong_day.isoformat(),
            "ends_at": (wrong_day + timedelta(hours=2)).isoformat(),
            "expected_audience": 30,
            "pitch": "Outside host day.",
        }, format="json")
        self.assertEqual(bad_day.status_code, 400)
        self.assertIn("not available", bad_day.data["error"])

        late_start = starts_at.replace(hour=22, minute=30)
        bad_time = self.client.post("/api/spaces/bookings/", {
            "listing_id": listing.id,
            "starts_at": late_start.isoformat(),
            "ends_at": (late_start + timedelta(hours=1)).isoformat(),
            "expected_audience": 30,
            "pitch": "Runs past host close.",
        }, format="json")
        self.assertEqual(bad_time.status_code, 400)
        self.assertIn("host window", bad_time.data["error"])

    def test_booking_must_match_host_calendar_date(self):
        target_date = (timezone.now() + timedelta(days=10)).date()
        listing = self.create_live_listing(
            available_windows=[{"date": target_date.isoformat(), "start": "19:00", "end": "23:00"}],
        )
        self.client.force_authenticate(self.artist)

        starts_at = timezone.make_aware(
            datetime.combine(target_date, datetime.min.time()).replace(hour=20, minute=0),
            timezone.get_current_timezone(),
        )
        ends_at = starts_at + timedelta(hours=2)

        ok = self.client.post("/api/spaces/bookings/", {
            "listing_id": listing.id,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "expected_audience": 30,
            "pitch": "Calendar date inside host hours.",
        }, format="json")
        self.assertEqual(ok.status_code, 201)

        wrong_date = starts_at + timedelta(days=1)
        bad = self.client.post("/api/spaces/bookings/", {
            "listing_id": listing.id,
            "starts_at": wrong_date.isoformat(),
            "ends_at": (wrong_date + timedelta(hours=2)).isoformat(),
            "expected_audience": 30,
            "pitch": "Wrong date.",
        }, format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertIn("not available", bad.data["error"])

    def test_booking_can_include_artist_material_for_host_review(self):
        listing = self.create_live_listing()
        self.client.force_authenticate(self.artist)

        starts_at = timezone.now() + timedelta(days=4)
        ends_at = starts_at + timedelta(hours=2)

        response = self.client.post("/api/spaces/bookings/", {
            "listing_id": listing.id,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "expected_audience": 40,
            "pitch": "Two-set room show with local draw.",
            "material_url": "https://www.youtube.com/watch?v=demo123",
            "material_credit": "Live session — Forum Theatre",
        }, format="json")
        self.assertEqual(response.status_code, 201)

        booking = SpaceBooking.objects.get(id=response.data["booking"]["id"])
        self.assertEqual(booking.material_url, "https://www.youtube.com/watch?v=demo123")
        self.assertEqual(booking.material_credit, "Live session — Forum Theatre")

        self.client.force_authenticate(self.host)
        feed = self.client.get("/api/spaces/bookings/")
        record = next(item for item in feed.data["results"] if item["id"] == booking.id)
        self.assertEqual(record["material_url"], booking.material_url)
        self.assertEqual(record["material_credit"], booking.material_credit)

    def test_confirmed_booking_gets_ticket_product(self):
        listing = self.create_live_listing()
        self.client.force_authenticate(self.artist)
        starts_at = timezone.now() + timedelta(days=5)
        ends_at = starts_at + timedelta(hours=2)

        create = self.client.post("/api/spaces/bookings/", {
            "listing_id": listing.id,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "expected_audience": 30,
            "pitch": "IndieFund ticketed show.",
            "ticket_price": "12.00",
        }, format="json")
        self.assertEqual(create.status_code, 201)
        booking = SpaceBooking.objects.get(id=create.data["booking"]["id"])

        self.client.force_authenticate(self.host)
        confirm = self.client.post(f"/api/spaces/bookings/{booking.id}/status/", {
            "status": SpaceBooking.CONFIRMED,
        }, format="json")
        self.assertEqual(confirm.status_code, 200)

        booking.refresh_from_db()
        self.assertTrue(booking.ticket_product_id)
        self.assertEqual(str(booking.ticket_product.price), "12.00")
        self.assertEqual(booking.ticket_product.product_type, Product.EVENT_TICKET)
        self.assertEqual(str(booking.ticket_product.platform_fee), "1.80")
        self.assertEqual(str(booking.ticket_product.host_share), "3.00")
        self.assertEqual(str(booking.ticket_product.artist_share), "7.20")

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_ticket_purchase_credits_host_door_share(self):
        listing = self.create_live_listing(booking_mode=SpaceListing.INSTANT_BOOK)
        self.client.force_authenticate(self.artist)
        starts_at = timezone.now() + timedelta(days=3)
        ends_at = starts_at + timedelta(hours=2)
        create = self.client.post("/api/spaces/bookings/", {
            "listing_id": listing.id,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "ticket_price": "12.00",
        }, format="json")
        booking = SpaceBooking.objects.get(id=create.data["booking"]["id"])

        self.client.force_authenticate(self.fan)
        purchase = self.client.post("/api/marketplace/checkout/", {"product_id": booking.ticket_product_id}, format="json")
        self.assertEqual(purchase.status_code, 201)
        self.assertEqual(purchase.data["host_share"], "3.00")

        host_profile = HostProfile.objects.get(user=self.host)
        self.assertEqual(str(host_profile.pending_ticket_earnings), "3.00")

    def create_presale_booking(self, presale_hours=24):
        listing = self.create_live_listing(booking_mode=SpaceListing.INSTANT_BOOK)
        self.client.force_authenticate(self.artist)
        starts_at = timezone.now() + timedelta(days=3)
        create = self.client.post("/api/spaces/bookings/", {
            "listing_id": listing.id,
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(hours=2)).isoformat(),
            "ticket_price": "12.00",
            "supporter_presale_hours": presale_hours,
        }, format="json")
        self.assertEqual(create.status_code, 201)
        return SpaceBooking.objects.get(id=create.data["booking"]["id"])

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_presale_blocks_non_supporters_until_window_ends(self):
        booking = self.create_presale_booking()
        self.assertEqual(booking.supporter_presale_hours, 24)
        self.assertIsNotNone(booking.tickets_on_sale_at)

        self.client.force_authenticate(self.fan)
        blocked = self.client.post("/api/marketplace/checkout/", {"product_id": booking.ticket_product_id}, format="json")
        self.assertEqual(blocked.status_code, 403)
        self.assertTrue(blocked.data["presale_only"])
        self.assertEqual(blocked.data["artist_username"], "artist")

        SpaceBooking.objects.filter(id=booking.id).update(
            tickets_on_sale_at=timezone.now() - timedelta(hours=25),
        )
        open_sale = self.client.post("/api/marketplace/checkout/", {"product_id": booking.ticket_product_id}, format="json")
        self.assertEqual(open_sale.status_code, 201)

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_presale_admits_supporters_immediately(self):
        booking = self.create_presale_booking()
        FanSubscription.objects.create(
            fan=self.fan,
            artist=self.artist,
            active=True,
            monthly_amount="3.00",
        )

        self.client.force_authenticate(self.fan)
        purchase = self.client.post("/api/marketplace/checkout/", {"product_id": booking.ticket_product_id}, format="json")
        self.assertEqual(purchase.status_code, 201)

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_zero_presale_hours_keeps_general_sale_open(self):
        booking = self.create_presale_booking(presale_hours=0)

        self.client.force_authenticate(self.fan)
        purchase = self.client.post("/api/marketplace/checkout/", {"product_id": booking.ticket_product_id}, format="json")
        self.assertEqual(purchase.status_code, 201)

    def test_booking_feed_exposes_presale_fields(self):
        booking = self.create_presale_booking()

        self.client.force_authenticate(self.artist)
        feed = self.client.get("/api/spaces/bookings/")
        record = next(item for item in feed.data["results"] if item["id"] == booking.id)
        self.assertEqual(record["supporter_presale_hours"], 24)
        self.assertIsNotNone(record["tickets_on_sale_at"])
        self.assertIsNotNone(record["presale_ends_at"])

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_host_stub_and_fan_check_in_at_door(self):
        from spaces.models import ShowCheckIn, ShowTicketStub

        listing = self.create_live_listing(booking_mode=SpaceListing.INSTANT_BOOK)
        self.client.force_authenticate(self.artist)
        starts_at = timezone.now() + timedelta(days=3)
        ends_at = starts_at + timedelta(hours=2)
        create = self.client.post("/api/spaces/bookings/", {
            "listing_id": listing.id,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "ticket_price": "10.00",
        }, format="json")
        booking = SpaceBooking.objects.get(id=create.data["booking"]["id"])

        self.client.force_authenticate(self.fan)
        checkout = self.client.post("/api/marketplace/checkout/", {"product_id": booking.ticket_product_id}, format="json")
        self.assertEqual(checkout.status_code, 201)
        self.assertNotIn("door_code", checkout.data)

        missing_stub = self.client.post(
            f"/api/spaces/bookings/{booking.id}/check-in/",
            {"stub_code": "BAD123"},
            format="json",
        )
        self.assertEqual(missing_stub.status_code, 400)

        self.client.force_authenticate(self.host)
        stub_res = self.client.post(f"/api/spaces/bookings/{booking.id}/ticket-stub/", {}, format="json")
        self.assertEqual(stub_res.status_code, 201)
        stub_code = stub_res.data["stub_code"]
        self.assertEqual(len(stub_code), 6)
        self.assertEqual(ShowTicketStub.objects.filter(booking=booking).count(), 1)

        self.client.force_authenticate(self.fan)
        checked_in = self.client.post(
            f"/api/spaces/bookings/{booking.id}/check-in/",
            {"stub_code": stub_code},
            format="json",
        )
        self.assertEqual(checked_in.status_code, 200)
        self.assertTrue(checked_in.data["checked_in"])
        booking.refresh_from_db()
        self.assertEqual(booking.attendance_checked_in, 1)
        self.assertTrue(ShowCheckIn.objects.filter(booking=booking, fan=self.fan).exists())

        reused = self.client.post(
            f"/api/spaces/bookings/{booking.id}/check-in/",
            {"stub_code": stub_code},
            format="json",
        )
        self.assertEqual(reused.status_code, 200)
        self.assertTrue(reused.data["checked_in"])

        self.client.force_authenticate(self.host)
        feed = self.client.get("/api/spaces/bookings/")
        record = next(item for item in feed.data["results"] if item["id"] == booking.id)
        self.assertEqual(record["tickets_verified_at_door"], 1)
        self.assertEqual(record["stubs_redeemed"], 1)

    def test_confirming_already_confirmed_booking_does_not_double_credit_challenge(self):
        from challenges.models import ArtistChallengeProgress, ChallengeTemplate
        from challenges.services import ensure_default_templates

        ensure_default_templates()
        listing = self.create_live_listing(booking_mode=SpaceListing.INSTANT_BOOK)
        starts_at = timezone.now() + timedelta(days=4)
        ends_at = starts_at + timedelta(hours=2)

        self.client.force_authenticate(self.artist)
        create = self.client.post("/api/spaces/bookings/", {
            "listing_id": listing.id,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "publish_to_calendar": True,
        }, format="json")
        booking = SpaceBooking.objects.get(id=create.data["booking"]["id"])
        progress = ArtistChallengeProgress.objects.get(
            artist=self.artist,
            template__metric="spaces_booking",
        )
        self.assertEqual(progress.progress, 1)

        self.client.force_authenticate(self.host)
        repeat = self.client.post(f"/api/spaces/bookings/{booking.id}/status/", {
            "status": SpaceBooking.CONFIRMED,
            "publish_to_calendar": True,
        }, format="json")
        self.assertEqual(repeat.status_code, 200)
        progress.refresh_from_db()
        self.assertEqual(progress.progress, 1)

    def test_host_registration_is_allowed(self):
        response = self.client.post("/api/accounts/register/", {
            "username": "venue",
            "password": "password123",
            "display_name": "Venue",
            "email": "venue@example.com",
            "user_type": "host",
            "discovery_location": "Melbourne",
            "terms_accepted": True,
        }, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["user"]["user_type"], User.HOST)
        self.assertTrue(response.data["user"]["is_host"])

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_fan_check_in_requires_ticket(self):
        from marketplace.models import Product

        listing = self.create_live_listing(booking_mode=SpaceListing.INSTANT_BOOK)
        ticket = Product.objects.create(
            artist=self.artist,
            title="Door",
            product_type=Product.EVENT_TICKET,
            price="10.00",
        )
        starts_at = timezone.now() + timedelta(days=1)
        booking = SpaceBooking.objects.create(
            listing=listing,
            artist=self.artist,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=2),
            status=SpaceBooking.CONFIRMED,
            ticket_product=ticket,
        )

        self.client.force_authenticate(self.fan)
        blocked = self.client.post(
            f"/api/spaces/bookings/{booking.id}/check-in/",
            {"stub_code": "ABC123"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 403)

        self.client.post("/api/marketplace/checkout/", {"product_id": ticket.id}, format="json")
        self.client.force_authenticate(self.host)
        stub_res = self.client.post(f"/api/spaces/bookings/{booking.id}/ticket-stub/", {}, format="json")
        self.assertEqual(stub_res.status_code, 201)

        self.client.force_authenticate(self.fan)
        ok = self.client.post(
            f"/api/spaces/bookings/{booking.id}/check-in/",
            {"stub_code": stub_res.data["stub_code"]},
            format="json",
        )
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(ok.data["checked_in"])
        booking.refresh_from_db()
        self.assertEqual(booking.attendance_checked_in, 1)

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_host_bookings_feed_reports_ticket_sales(self):
        from marketplace.models import Product

        listing = self.create_live_listing(booking_mode=SpaceListing.INSTANT_BOOK, capacity=40)
        ticket = Product.objects.create(
            artist=self.artist,
            title="Door",
            product_type=Product.EVENT_TICKET,
            price="10.00",
        )
        starts_at = timezone.now() + timedelta(days=2)
        booking = SpaceBooking.objects.create(
            listing=listing,
            artist=self.artist,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=2),
            status=SpaceBooking.CONFIRMED,
            ticket_product=ticket,
        )

        self.client.force_authenticate(self.fan)
        self.client.post("/api/marketplace/checkout/", {"product_id": ticket.id}, format="json")

        self.client.force_authenticate(self.host)
        response = self.client.get("/api/spaces/bookings/")
        self.assertEqual(response.status_code, 200)
        record = next(item for item in response.data["results"] if item["id"] == booking.id)
        self.assertEqual(record["tickets_sold"], 1)
        self.assertEqual(record["tickets_capacity"], 40)
        self.assertEqual(record["tickets_remaining"], 39)
        self.assertFalse(record["tickets_sold_out"])
        self.assertEqual(record["ticket_title"], "Door")

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_fan_can_review_completed_show(self):
        from marketplace.models import Product
        from notifications.models import Notification

        listing = self.create_live_listing(booking_mode=SpaceListing.INSTANT_BOOK)
        ticket = Product.objects.create(
            artist=self.artist,
            title="Door",
            product_type=Product.EVENT_TICKET,
            price="10.00",
        )
        starts_at = timezone.now() - timedelta(days=1)
        booking = SpaceBooking.objects.create(
            listing=listing,
            artist=self.artist,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=2),
            status=SpaceBooking.COMPLETED,
            ticket_product=ticket,
        )

        self.client.force_authenticate(self.fan)
        self.client.post("/api/marketplace/checkout/", {"product_id": ticket.id}, format="json")

        from spaces.show_night import notify_post_show_review_prompts

        count = notify_post_show_review_prompts(booking)
        self.assertEqual(count, 1)
        self.assertTrue(
            Notification.objects.filter(recipient=self.fan, target_url__contains=str(booking.id)).exists()
        )

        review = self.client.post(f"/api/spaces/bookings/{booking.id}/reviews/", {
            "reviewee_type": "show",
            "rating": 5,
            "comment": "Great room and vibe.",
        }, format="json")
        self.assertEqual(review.status_code, 201)

    def test_host_can_dismiss_and_clear_confirmed_history(self):
        listing = self.create_live_listing()
        starts_at = timezone.now() + timedelta(days=2)
        booking = SpaceBooking.objects.create(
            listing=listing,
            artist=self.artist,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=2),
            status=SpaceBooking.CONFIRMED,
        )

        self.client.force_authenticate(self.host)
        dismiss = self.client.post(f"/api/spaces/bookings/{booking.id}/dismiss/", {}, format="json")
        self.assertEqual(dismiss.status_code, 200)

        feed = self.client.get("/api/spaces/bookings/")
        self.assertEqual(feed.data["count"], 0)

        booking.refresh_from_db()
        self.assertIsNotNone(booking.dismissed_by_host_at)

    def test_artist_can_clear_booking_list(self):
        listing = self.create_live_listing()
        starts_at = timezone.now() + timedelta(days=2)
        SpaceBooking.objects.create(
            listing=listing,
            artist=self.artist,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=2),
            status=SpaceBooking.REQUESTED,
        )
        SpaceBooking.objects.create(
            listing=listing,
            artist=self.artist,
            starts_at=starts_at + timedelta(days=3),
            ends_at=starts_at + timedelta(days=3, hours=2),
            status=SpaceBooking.COMPLETED,
        )

        self.client.force_authenticate(self.artist)
        clear = self.client.post("/api/spaces/bookings/clear/", {"scope": "all"}, format="json")
        self.assertEqual(clear.status_code, 200)
        self.assertEqual(clear.data["cleared"], 2)

        feed = self.client.get("/api/spaces/bookings/")
        self.assertEqual(feed.data["count"], 0)

    def test_artist_can_request_recurring_series(self):
        date_a = (timezone.now() + timedelta(days=14)).date()
        date_b = date_a + timedelta(days=7)
        listing = self.create_live_listing(
            available_windows=[
                {"date": date_a.isoformat(), "start": "19:00", "end": "23:00"},
                {"date": date_b.isoformat(), "start": "19:00", "end": "23:00"},
            ],
        )
        self.client.force_authenticate(self.artist)

        starts_a = timezone.make_aware(
            datetime.combine(date_a, datetime.min.time()).replace(hour=20, minute=0),
            timezone.get_current_timezone(),
        )
        ends_a = starts_a + timedelta(hours=2)
        starts_b = timezone.make_aware(
            datetime.combine(date_b, datetime.min.time()).replace(hour=20, minute=0),
            timezone.get_current_timezone(),
        )
        ends_b = starts_b + timedelta(hours=2)

        response = self.client.post("/api/spaces/bookings/", {
            "listing_id": listing.id,
            "dates": [
                {"starts_at": starts_a.isoformat(), "ends_at": ends_a.isoformat()},
                {"starts_at": starts_b.isoformat(), "ends_at": ends_b.isoformat()},
            ],
            "expected_audience": 35,
            "pitch": "Two-night residency.",
        }, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertIn("series", response.data["message"].lower())
        self.assertIsNotNone(response.data["series_id"])
        self.assertEqual(len(response.data["bookings"]), 2)
        bookings = SpaceBooking.objects.filter(series_id=response.data["series_id"]).order_by("starts_at")
        self.assertEqual(bookings.count(), 2)
        self.assertEqual(bookings[0].pitch, "Two-night residency.")
        self.assertEqual(str(bookings[0].series_id), response.data["series_id"])

