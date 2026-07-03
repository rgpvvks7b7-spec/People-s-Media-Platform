from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from accounts.beta_report import build_beta_feedback_report, format_beta_feedback_report
from accounts.models import BetaFeedback
from artists.models import ArtistProfile
from spaces.models import HostProfile, SpaceListing
from spaces.placeholder_photos import ensure_listing_gallery

User = get_user_model()


BETA_LOOP_FEEDBACK = [
    # fan personas
    ("demo_fan", "navigation", "medium", "/?page=discover", "Playing near you needs venue context", "Gig cards show the artist but not the cafe or suburb until you tap through."),
    ("fan_indie_mel", "content", "medium", "/?page=spaces", "Space reviews should show host reply option", "After leaving a rating, fans expect to see whether the venue responded."),
    ("fan_rnb_syd", "payments", "high", "/?artist=static_harbor", "Buy button needs clearer purchase confirmation", "Marketplace purchase succeeds but there is no receipt or order summary on screen."),
    ("fan_beatmaker_bri", "content", "low", "/?artist=luna_lane", "Sample pack preview is enough for beta", "Demo purchase flow works; would like waveform preview before buying packs."),
    ("fan_newcomer", "setup", "blocker", "/?page=profile", "New fan cannot find first action path", "Empty home screen still does not explain save, support, or discover in one guided path."),
    ("fan_power_user", "navigation", "medium", "/?page=saved", "Saved artists should surface playing near you", "Local gig widget is on discover but not on saved artists where power users live."),
    ("fan_mobile_first", "navigation", "high", "/?page=profile", "Beta feedback form is below the fold on mobile", "Testers on phone had to scroll past preferences before finding the beta report form."),
    ("fan_subscriber", "content", "medium", "/?artist=luna_lane", "Supporter-only tab label is clear", "Subscriber-only music lock messaging is understandable; keep the green badge."),
    ("demo_fan", "navigation", "medium", "/?page=my-scene", "My Scene supported tab shows gig from Marlo Saints", "After beta_scene_loop seed, supported tab should list Harbour Room booking with ticket link."),
    ("fan_indie_mel", "navigation", "low", "/?page=my-scene", "Gig notification deep link opens show detail", "Bell alert should land on my-scene show modal, not generic Spaces page."),
    ("fan_folk_ade", "other", "low", "/?page=discover", "Discovery health badges are helpful", "Business-health score helped compare artists; tooltip could explain the ratio."),
    # artist personas
    ("luna_lane", "content", "high", "/?page=profile", "Trust banner should link to flagged uploads", "AI review flags list titles but do not jump to the upload to fix disclosure."),
    ("static_harbor", "payments", "medium", "/?page=profile", "Pro insights need weekly trend line", "MRR forecast number is useful; a simple up/down vs last week would help."),
    ("mika_north", "setup", "medium", "/?page=profile", "Profile completion checklist still missing steps", "Trust banner says complete profile but does not list missing fields."),
    ("river_kite", "content", "medium", "/?page=spaces", "Event ticket dropdown needs short help text", "Booking a space with a ticket product is powerful but the link field is unexplained."),
    ("velvet_parade", "payments", "high", "/?page=profile", "Dashboard marketplace sales finally track purchases", "Monthly sales total updates after demo purchase — good for beta validation."),
    ("marlo_saints", "navigation", "medium", "/?artist=marlo_saints", "Calendar sync from space booking works", "Confirmed gig appeared on artist calendar; iCal export should mention venue timezone."),
    # host persona
    ("beta_host_cafe", "setup", "high", "/?page=profile", "Host listing form needs min supporters explainer", "min_local_supporters field exists but hosts do not know it uses venue city counts."),
    ("beta_host_cafe", "navigation", "medium", "/?page=spaces", "Host booking inbox needs artist draw preview", "When reviewing requests, show local supporter count before confirm."),
    ("beta_host_cafe", "payments", "low", "/?page=spaces", "F&B-only split type is clear for venues", "Hosts understood they keep bar revenue; platform fee on tickets is acceptable."),
    # cross-cutting
    ("luna_lane", "payments", "blocker", "/?page=spaces", "Artist blocked by min supporters without growth tips", "Booking rejected for low local supporters but dashboard does not say how to grow local fans."),
]


class Command(BaseCommand):
    help = "Seed mock beta personas, simulate feedback submissions, and print an aggregated report."

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed",
            action="store_true",
            help="Run seed_demo first so artists, fans, and content exist.",
        )
        parser.add_argument(
            "--reset-loop",
            action="store_true",
            help="Remove prior loop submissions (matched by summary) before inserting fresh feedback.",
        )

    def handle(self, *args, **options):
        if options["seed"]:
            self.stdout.write("Running seed_demo...")
            call_command("seed_demo")

        self.ensure_beta_personas()

        if options["reset_loop"]:
            summaries = [row[4] for row in BETA_LOOP_FEEDBACK]
            deleted, _ = BetaFeedback.objects.filter(summary__in=summaries).delete()
            self.stdout.write(f"Removed {deleted} prior loop feedback rows.")

        created = self.seed_loop_feedback()
        report = build_beta_feedback_report()

        self.stdout.write(self.style.SUCCESS(f"Recorded {created} beta loop feedback submissions."))
        self.stdout.write(format_beta_feedback_report(report))

    def ensure_beta_personas(self):
        host = self.upsert_demo_user(
            username="beta_host_cafe",
            password="demo12345",
            user_type=User.HOST,
            display_name="Harbour Room Host",
            is_beta_tester=True,
            beta_notes="Host beta tester: list a space, set min local supporters, confirm bookings, and review artist draw.",
        )

        HostProfile.objects.update_or_create(
            user=host,
            defaults={
                "business_name": "Harbour Room",
                "contact_email": "host@harbourroom.demo",
                "address": "12 Bay Street",
                "city": "Melbourne",
                "verified": True,
            },
        )
        listing, _ = SpaceListing.objects.update_or_create(
            host=host,
            name="Harbour Room — Sunday Sessions",
            defaults={
                "description": "Cafe back room with PA, 40 seats, and full bar for intimate gigs.",
                "address": "12 Bay Street, Melbourne",
                "city": "Melbourne",
                "capacity": 40,
                "available_windows": [{"day": "sun", "start": "14:00", "end": "18:00"}],
                "tags": ["acoustic", "cafe", "indie"],
                "bar_open": True,
                "kitchen_open": True,
                "split_type": SpaceListing.DOOR_PERCENT,
                "host_cut_percent": 15,
                "booking_mode": SpaceListing.REQUEST,
                "min_local_supporters": 3,
                "status": SpaceListing.LIVE,
            },
        )
        ensure_listing_gallery(listing)

        artist = self.upsert_demo_user(
            username="beta_artist_gigs",
            password="demo12345",
            user_type=User.ARTIST,
            display_name="Gigs Beta Artist",
            is_beta_tester=True,
            beta_notes="Artist beta tester: book Harbour Room, attach event ticket, confirm calendar sync, submit trust feedback.",
        )

        ArtistProfile.objects.update_or_create(
            owner=artist,
            defaults={
                "stage_name": "Gigs Beta Artist",
                "genre": "Indie Pop",
                "city": "Melbourne",
                "artist_story": "Beta persona for spaces booking, calendar, and local draw flows.",
                "influences": "Demo only",
            },
        )

        self.upsert_demo_user(
            username="beta_admin",
            password="demo12345",
            user_type=User.ADMIN,
            display_name="Beta Admin",
            is_staff=True,
            is_superuser=True,
            is_beta_tester=False,
        )

    def upsert_demo_user(self, username, password, user_type, display_name, **fields):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "user_type": user_type,
                "display_name": display_name,
                **fields,
            },
        )
        user.user_type = user_type
        user.display_name = display_name
        for field, value in fields.items():
            setattr(user, field, value)
        user.set_password(password)
        user.save()
        return user

    def seed_loop_feedback(self):
        created = 0
        for username, category, severity, path, summary, details in BETA_LOOP_FEEDBACK:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Skipping feedback for missing user {username}"))
                continue

            _, was_created = BetaFeedback.objects.update_or_create(
                user=user,
                summary=summary,
                defaults={
                    "category": category,
                    "severity": severity,
                    "path": path,
                    "details": details,
                    "resolved": False,
                },
            )
            user.is_beta_tester = True
            user.save(update_fields=["is_beta_tester"])
            if was_created:
                created += 1
        return created
