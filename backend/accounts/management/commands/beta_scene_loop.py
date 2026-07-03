"""
Autonomous beta harness for the Local Show Loop (My Scene + gig notifications).

Usage:
  python manage.py beta_scene_loop --seed
  python manage.py beta_scene_loop --reset-notifications
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from artistcalendar.models import ArtistCalendarItem
from artists.models import ArtistFanContact, ArtistProfile
from marketplace.models import Product
from notifications.gig_notifications import notify_local_supporters_for_booking
from notifications.models import Notification
from spaces.models import HostProfile, SpaceBooking, SpaceListing
from spaces.placeholder_photos import ensure_listing_gallery
from spaces.services import on_booking_confirmed
from subscriptions.models import FanSubscription


User = get_user_model()

LAUNCH_CITY = "Melbourne"
DEMO_PASSWORD = "demo12345"

BETA_FAN_USERNAMES = ("demo_fan", "fan_indie_mel", "fan_subscriber")
GIG_ARTIST_USERNAME = "marlo_saints"
HOST_USERNAME = "team_host"
LISTING_NAME = "Harbour Room — Sunday Sessions"


class Command(BaseCommand):
    help = "Seed and autonomously verify the Local Show Loop beta scenario (My Scene + gig alerts)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed",
            action="store_true",
            help="Run seed_demo before setting up the scene loop fixtures.",
        )
        parser.add_argument(
            "--reset-notifications",
            action="store_true",
            help="Clear GIG notifications for the demo booking before re-notifying.",
        )
        parser.add_argument(
            "--skip-notify",
            action="store_true",
            help="Only seed data; do not send gig notifications.",
        )
        parser.add_argument(
            "--seed-only",
            action="store_true",
            help="Only seed scene fixtures; skip autonomous API/email checks.",
        )

    def handle(self, *args, **options):
        if options["seed"]:
            self.stdout.write("Running seed_demo…")
            call_command("seed_demo")

        context = self.ensure_scene_fixtures()
        if options["reset_notifications"]:
            deleted, _ = Notification.objects.filter(
                notification_type=Notification.GIG,
                target_url__contains=f"show={context['booking'].id}",
            ).delete()
            self.stdout.write(f"Cleared {deleted} prior gig notification(s).")

        if not options["skip_notify"]:
            with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
                result = notify_local_supporters_for_booking(context["booking"], force=True)
            self.stdout.write(
                f"Gig notify: in-app={result['notified_count']} email={result['email_count']} "
                f"(skipped={result.get('skipped')}, reason={result.get('reason') or 'none'})"
            )

        checks = []
        if not options["seed_only"]:
            checks = self.run_autonomous_checks(context)
        self.print_report(context, checks)

        if options["seed_only"]:
            self.stdout.write(self.style.SUCCESS("Beta scene loop seeded — checks skipped."))
            return

        failed = [name for name, ok, _ in checks if not ok]
        if failed:
            self.stdout.write(self.style.ERROR(f"Beta scene loop FAILED ({len(failed)} check(s))."))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("Beta scene loop PASSED — ready for human spot-check."))

    def ensure_scene_fixtures(self):
        host = self._upsert_user(
            HOST_USERNAME,
            User.HOST,
            "Harbour Room Host",
            beta_notes="Host beta: confirm bookings, review local draw, check attendance.",
        )
        HostProfile.objects.update_or_create(
            user=host,
            defaults={
                "business_name": "Harbour Room",
                "contact_email": "host@harbourroom.demo",
                "address": "12 Bay Street",
                "city": LAUNCH_CITY,
                "verified": True,
            },
        )

        listing, _ = SpaceListing.objects.update_or_create(
            host=host,
            name=LISTING_NAME,
            defaults={
                "description": "Cafe back room with PA, 40 seats, and full bar for intimate gigs.",
                "address": "12 Bay Street, Melbourne",
                "city": LAUNCH_CITY,
                "capacity": 40,
                "available_windows": [{"day": "sun", "start": "14:00", "end": "18:00"}],
                "tags": ["acoustic", "cafe", "indie"],
                "bar_open": True,
                "kitchen_open": True,
                "drink_minimum": "One drink minimum",
                "split_type": SpaceListing.DOOR_PERCENT,
                "host_cut_percent": 15,
                "booking_mode": SpaceListing.REQUEST,
                "min_local_supporters": 2,
                "status": SpaceListing.LIVE,
            },
        )
        ensure_listing_gallery(listing)

        artist = User.objects.filter(username=GIG_ARTIST_USERNAME, user_type=User.ARTIST).first()
        if not artist:
            artist = self._upsert_user(
                GIG_ARTIST_USERNAME,
                User.ARTIST,
                "Marlo Saints",
                beta_notes="Melbourne artist beta: local draw + gig booking loop.",
            )
            ArtistProfile.objects.update_or_create(
                owner=artist,
                defaults={
                    "stage_name": "Marlo Saints",
                    "genre": "Alt R&B",
                    "city": LAUNCH_CITY,
                    "artist_story": "Beta persona for local gig and My Scene flows.",
                    "influences": "Demo only",
                },
            )

        melbourne_fans = []
        for username in BETA_FAN_USERNAMES:
            fan = User.objects.filter(username=username).first()
            if not fan:
                fan = self._upsert_user(
                    username,
                    User.FAN,
                    username.replace("_", " ").title(),
                    discovery_location=LAUNCH_CITY,
                    favorite_genres="indie pop, alt R&B",
                    is_beta_tester=True,
                    beta_notes="Fan beta: open My Scene, verify gig alerts from supported artists.",
                )
            elif not fan.discovery_location:
                fan.discovery_location = LAUNCH_CITY
                fan.is_beta_tester = True
                fan.save(update_fields=["discovery_location", "is_beta_tester"])
            melbourne_fans.append(fan)

        for fan in melbourne_fans:
            FanSubscription.objects.update_or_create(
                fan=fan,
                artist=artist,
                defaults={
                    "monthly_amount": Decimal("3.00"),
                    "active": True,
                    "payment_provider": "demo",
                    "stripe_status": "active",
                },
            )

        demo_fan = melbourne_fans[0]
        contact, _ = ArtistFanContact.objects.get_or_create(artist=artist, fan=demo_fan)
        if not contact.email_shared:
            contact.share(ArtistFanContact.SUPPORT_PROMPT)
            contact.save()
        if not demo_fan.email:
            demo_fan.email = "demo_fan@indiefund.local"
            demo_fan.save(update_fields=["email"])

        starts_at = timezone.now() + timedelta(days=7)
        ends_at = starts_at + timedelta(hours=2)
        booking = (
            SpaceBooking.objects.filter(
                listing=listing,
                artist=artist,
            )
            .order_by("-updated_at")
            .first()
        )
        if booking:
            booking.starts_at = starts_at
            booking.ends_at = ends_at
            booking.expected_audience = 35
            booking.pitch = "Beta local supporters night — intimate Alt R&B set with full band."
            if booking.status != SpaceBooking.COMPLETED:
                booking.status = SpaceBooking.CONFIRMED
            booking.save()
        else:
            booking = SpaceBooking.objects.create(
                listing=listing,
                artist=artist,
                starts_at=starts_at,
                ends_at=ends_at,
                expected_audience=35,
                pitch="Beta local supporters night — intimate Alt R&B set with full band.",
                status=SpaceBooking.CONFIRMED,
            )

        ticket, _ = Product.objects.update_or_create(
            artist=artist,
            title="Harbour Room Live — Cover",
            defaults={
                "product_type": Product.EVENT_TICKET,
                "description": "Entry for the Sunday session at Harbour Room.",
                "price": Decimal("15.00"),
                "is_active": True,
            },
        )
        booking.ticket_product = ticket
        booking.save(update_fields=["ticket_product", "updated_at"])

        on_booking_confirmed(booking, publish_to_calendar=True, calendar_visibility=ArtistCalendarItem.PUBLIC)

        local_subs = FanSubscription.objects.filter(
            artist=artist,
            active=True,
            fan__discovery_location__iexact=LAUNCH_CITY,
        ).count()

        return {
            "host": host,
            "listing": listing,
            "artist": artist,
            "fans": melbourne_fans,
            "booking": booking,
            "ticket": ticket,
            "local_subscribers": local_subs,
        }

    def run_autonomous_checks(self, context):
        with override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"]):
            return self._run_autonomous_checks(context)

    def _run_autonomous_checks(self, context):
        client = APIClient()
        booking = context["booking"]
        artist = context["artist"]
        demo_fan = context["fans"][0]
        checks = []

        client.force_authenticate(demo_fan)
        scene = client.get("/api/discovery/my-scene/")
        checks.append((
            "my_scene_endpoint",
            scene.status_code == 200,
            f"status={scene.status_code}",
        ))
        if scene.status_code == 200:
            data = scene.json()
            checks.append((
                "my_scene_has_local_shows",
                data.get("counts", {}).get("all", 0) >= 1,
                f"all={data.get('counts', {}).get('all')}",
            ))
            checks.append((
                "my_scene_supported_tab",
                data.get("counts", {}).get("supported", 0) >= 1,
                f"supported={data.get('counts', {}).get('supported')}",
            ))
            checks.append((
                "my_scene_location",
                data.get("location") == LAUNCH_CITY,
                f"location={data.get('location')}",
            ))

        detail = client.get(f"/api/discovery/shows/{booking.id}/")
        detail_show = detail.json().get("show", {}) if detail.status_code == 200 else {}
        checks.append((
            "show_detail_endpoint",
            detail.status_code == 200 and detail_show.get("booking_id") == booking.id,
            f"status={detail.status_code} ended={detail_show.get('has_ended')}",
        ))

        gig_notes = Notification.objects.filter(
            recipient=demo_fan,
            notification_type=Notification.GIG,
            target_url__contains=f"show={booking.id}",
        ).count()
        checks.append((
            "fan_gig_notification",
            gig_notes >= 1,
            f"count={gig_notes}",
        ))

        calendar_ok = ArtistCalendarItem.objects.filter(
            space_booking=booking,
            item_type=ArtistCalendarItem.GIG,
            visibility=ArtistCalendarItem.PUBLIC,
        ).exists()
        checks.append(("calendar_item_public", calendar_ok, ""))

        client.force_authenticate(context["host"])
        host_bookings = client.get("/api/spaces/bookings/")
        host_has_booking = any(
            item.get("id") == booking.id
            for item in host_bookings.json().get("results", [])
        )
        checks.append(("host_sees_booking", host_bookings.status_code == 200 and host_has_booking, ""))

        client.force_authenticate(artist)
        draw = client.get(f"/api/spaces/artists/{artist.id}/draw-profile/?venue_city={LAUNCH_CITY}")
        checks.append((
            "artist_local_draw",
            draw.status_code == 200 and draw.json().get("local_supporters", 0) >= 2,
            f"local={draw.json().get('local_supporters') if draw.status_code == 200 else 'n/a'}",
        ))

        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            from django.core import mail

            outbox = getattr(mail, "outbox", None)
            if outbox is not None:
                outbox.clear()
                notify_local_supporters_for_booking(booking, reminder=True, force=True)
                checks.append((
                    "email_to_opted_in_fan",
                    any("demo_fan@indiefund.local" in msg.to for msg in outbox),
                    f"sent={len(outbox)}",
                ))
            else:
                checks.append(("email_to_opted_in_fan", True, "skipped (no locmem outbox)"))

        return checks

    def print_report(self, context, checks):
        booking = context["booking"]
        artist_profile = getattr(context["artist"], "artist_profile", None)
        stage_name = artist_profile.stage_name if artist_profile else context["artist"].username
        frontend = "http://localhost:5173"

        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("=== Local Show Loop — Beta Playbook ==="))
        self.stdout.write(f"City: {LAUNCH_CITY}")
        self.stdout.write(f"Show: {stage_name} @ {context['listing'].name}")
        self.stdout.write(f"When: {booking.starts_at.strftime('%a %b %d · %I:%M %p')}")
        self.stdout.write(f"Local subscribers: {context['local_subscribers']}")
        self.stdout.write("")
        self.stdout.write("Log in (password demo12345 for all demo accounts):")
        self.stdout.write(f"  Fan (start here):  demo_fan")
        self.stdout.write(f"  My Scene URL:      {frontend}/?page=my-scene")
        self.stdout.write(f"  Show deep link:    {frontend}/?page=my-scene&show={booking.id}")
        self.stdout.write(f"  Host inbox:        {HOST_USERNAME} → Spaces")
        self.stdout.write(f"  Artist:            {GIG_ARTIST_USERNAME}")
        self.stdout.write("")
        self.stdout.write("Autonomous checks:")
        for name, ok, detail in checks:
            line = f"  [{'PASS' if ok else 'FAIL'}] {name}"
            if detail:
                line += f" — {detail}"
            self.stdout.write(self.style.SUCCESS(line) if ok else self.style.ERROR(line))

    def _upsert_user(self, username, user_type, display_name, **fields):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={"user_type": user_type, "display_name": display_name, **fields},
        )
        user.user_type = user_type
        user.display_name = display_name
        for key, value in fields.items():
            setattr(user, key, value)
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user
