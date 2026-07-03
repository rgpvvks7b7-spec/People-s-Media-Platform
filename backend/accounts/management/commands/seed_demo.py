import io
import math
import wave
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from accounts.models import BetaFeedback
from artists.models import ArtistFollow, ArtistProfile
from discovery.models import ArtistSignal
from marketplace.models import Product
from mediahub.models import MusicUpload
from notifications.models import Notification
from posts.models import Comment, Like, Post
from spaces.models import HostProfile, SpaceBooking, SpaceListing
from spaces.placeholder_photos import ensure_listing_gallery
from subscriptions.models import FanSubscription


User = get_user_model()

BULK_CITIES = ("Melbourne", "Sydney", "Brisbane")
BULK_ARTIST_COUNT = 20
BULK_FAN_COUNT = 200
BULK_HOST_COUNT = 40
DEMO_PASSWORD = "demo12345"


class Command(BaseCommand):
    help = "Seed local demo users, artists, posts, music, products, and subscriptions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--launch-city",
            default="",
            help="Emphasize seed density for a launch city (e.g. Melbourne). Prints ops summary when set.",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._demo_wav_cache = {}
        self._cover_png_cache = {}

    def handle(self, *args, **options):
        fan = self.upsert_user(
            username="demo_fan",
            password="demo12345",
            user_type=User.FAN,
            display_name="Demo Fan",
            favorite_genres="indie pop, alt R&B, bedroom pop",
            discovery_location="Melbourne",
            is_beta_tester=True,
            beta_notes="Primary fan beta tester: verify discovery, saved artists, support flow, notifications, and profile preferences.",
        )
        fan_personas = [
            ("fan_indie_mel", "Indie Mel", "indie pop, bedroom pop, dream pop", "Melbourne"),
            ("fan_rnb_syd", "R&B Syd", "alt R&B, soul, electronic", "Sydney"),
            ("fan_beatmaker_bri", "Beatmaker Bri", "electronic, sample packs, synth pop", "Brisbane"),
            ("fan_folk_ade", "Folk Ade", "indie folk, singer songwriter, ambient", "Adelaide"),
            ("fan_newcomer", "Newcomer Fan", "", ""),
            ("fan_power_user", "Power User Fan", "indie rock, pop punk, dance pop", "Perth"),
            ("fan_mobile_first", "Mobile First Fan", "dream pop, synth pop, dance pop", "Canberra"),
            ("fan_subscriber", "Subscriber Fan", "indie pop, alt R&B, soul", "Melbourne"),
        ]
        fans = [fan]
        for username, display_name, favorite_genres, discovery_location in fan_personas:
            fans.append(self.upsert_user(
                username=username,
                password="demo12345",
                user_type=User.FAN,
                display_name=display_name,
                favorite_genres=favorite_genres,
                discovery_location=discovery_location,
                is_beta_tester=True,
                beta_notes=self.beta_notes_for(username),
            ))

        artist_luna = self.upsert_user(
            username="luna_lane",
            password="demo12345",
            user_type=User.ARTIST,
            display_name="Luna Lane",
            is_beta_tester=True,
            beta_notes="Artist beta tester: verify dashboard, profile setup, posts, uploads, store and fan preview.",
        )
        artist_static = self.upsert_user(
            username="static_harbor",
            password="demo12345",
            user_type=User.ARTIST,
            display_name="Static Harbor",
            is_beta_tester=True,
            beta_notes="Artist beta tester: verify subscriptions, supporter-only content and notification activity.",
        )
        artist_mika = self.upsert_user(
            username="mika_north",
            password="demo12345",
            user_type=User.ARTIST,
            display_name="Mika North",
            is_beta_tester=True,
            beta_notes="Artist beta tester: verify page-builder visibility toggles and fan-facing profile navigation.",
        )
        extra_artists = []
        for data in [
            ("river_kite", "River Kite", "Indie Folk", "Melbourne", "Fingerpicked folk songs with close harmonies and quiet room ambience.", "Big Thief, Phoebe Bridgers, Julia Jacklin"),
            ("velvet_parade", "Velvet Parade", "Dream Pop", "Sydney", "Wide guitars, soft drums, and chorus-heavy songs made for late train rides.", "Beach House, Hatchie, Slowdive"),
            ("juno_rift", "Juno Rift", "Electronic", "Brisbane", "Hardware synth sketches, vocal fragments, and bright club-adjacent instrumentals.", "Caribou, Four Tet, Kelly Lee Owens"),
            ("marlo_saints", "Marlo Saints", "Alt R&B", "Melbourne", "Smooth hooks, live guitar pockets, and honest writing around messy nights out.", "Frank Ocean, Dijon, Omar Apollo"),
            ("paper_tides", "Paper Tides", "Bedroom Pop", "Adelaide", "Small songs with tape hiss, clean guitars, and gentle morning melodies.", "Men I Trust, Alex G, Faye Webster"),
            ("noah_violet", "Noah Violet", "Indie Rock", "Perth", "Fuzzy indie rock with big bridge sections and restless drums.", "The Strokes, Wet Leg, Spacey Jane"),
            ("sol_avenue", "Sol Avenue", "Soul", "Melbourne", "Warm soul demos led by Rhodes chords, live bass, and stacked backing vocals.", "SAULT, Cleo Sol, D'Angelo"),
            ("cassia_blue", "Cassia Blue", "Singer Songwriter", "Hobart", "Direct lyric writing, nylon guitar, and intimate vocal takes.", "Laura Marling, Adrianne Lenker, Angie McMahon"),
            ("north_arcade", "North Arcade", "Synth Pop", "Canberra", "Polished synth pop hooks with punchy drums and bright vocal layers.", "CHVRCHES, MUNA, Robyn"),
            ("elara_fox", "Elara Fox", "Indie Pop", "Sydney", "Shimmering pop songs about distance, doubt, and getting out of your own way.", "Lorde, Maggie Rogers, BENEE"),
            ("atlas_wren", "Atlas Wren", "Ambient", "Brisbane", "Slow instrumental pieces built from piano loops, field recordings, and soft distortion.", "Nils Frahm, Brian Eno, Hania Rani"),
            ("golden_hourglass", "Golden Hourglass", "Psych Pop", "Fremantle", "Sun-baked psych pop with jangly guitars and loose harmonies.", "Tame Impala, Melody's Echo Chamber, Unknown Mortal Orchestra"),
            ("mia_afterdark", "Mia Afterdark", "Dance Pop", "Melbourne", "Night-drive pop with clean hooks, club drums, and glossy vocal stacks.", "Romy, Jessie Ware, Dua Lipa"),
            ("sadie_sparks", "Sadie Sparks", "Pop Punk", "Newcastle", "Fast guitars, diary lyrics, and shout-along choruses from a tiny rehearsal room.", "Paramore, The Beths, beabadoobee"),
        ]:
            username, display_name, genre, city, story, influences = data
            user = self.upsert_user(
                username=username,
                password="demo12345",
                user_type=User.ARTIST,
                display_name=display_name,
                is_beta_tester=True,
                beta_notes=f"Artist beta tester for {genre}: verify setup copy, discovery ranking and content tabs.",
            )
            extra_artists.append((user, {
                "stage_name": display_name,
                "genre": genre,
                "city": city,
                "artist_story": story,
                "influences": influences,
            }))

        self.upsert_artist_profile(
            artist_luna,
            stage_name="Luna Lane",
            genre="Indie Pop",
            city="Melbourne",
            artist_story="Warm synths, late-night vocals, and diary-style hooks from the inner north.",
            influences="Clairo, BENEE, The Japanese House",
            is_verified=True,
            professions="music,visual_art",
        )
        self.upsert_artist_profile(
            artist_static,
            stage_name="Static Harbor",
            genre="Alt R&B",
            city="Sydney",
            artist_story="Textured R&B sketches built around dusty keys, live bass, and patient choruses.",
            influences="Steve Lacy, SZA, Dijon",
        )
        self.upsert_artist_profile(
            artist_mika,
            stage_name="Mika North",
            genre="Bedroom Pop",
            city="Brisbane",
            artist_story="Small-room guitar pop with soft percussion and hooks that arrive sideways.",
            influences="Faye Webster, Alex G, Men I Trust",
        )
        for artist, profile_fields in extra_artists:
            self.upsert_artist_profile(artist, **profile_fields)

        bulk_artists = self.seed_bulk_artists()
        bulk_fans = self.seed_bulk_fans()

        FanSubscription.objects.update_or_create(
            fan=fan,
            artist=artist_luna,
            defaults={
                "monthly_amount": Decimal("3.00"),
                "billing_date": 16,
                "active": True,
                "payment_provider": "demo",
                "stripe_status": "active",
            },
        )
        artist_users = (
            [artist_luna, artist_static, artist_mika]
            + [artist for artist, _ in extra_artists]
            + bulk_artists
        )
        self.seed_fan_relationships(fans, artist_users)
        self.seed_bulk_fan_engagement(bulk_fans, artist_users)
        self.seed_beta_feedback(fans, artist_users)

        self.upsert_music(
            artist=artist_luna,
            title="Paper Moons",
            genre="Indie Pop",
            bpm=104,
            is_downloadable=True,
            is_subscriber_only=False,
        )
        self.upsert_music(
            artist=artist_luna,
            title="Afterparty Voice Memo",
            genre="Indie Pop",
            bpm=92,
            is_downloadable=False,
            is_subscriber_only=True,
        )
        self.upsert_music(
            artist=artist_static,
            title="Low Tide Keys",
            genre="Alt R&B",
            bpm=78,
            is_downloadable=False,
            is_subscriber_only=False,
        )
        self.upsert_music(
            artist=artist_mika,
            title="Window Seat",
            genre="Bedroom Pop",
            bpm=116,
            is_downloadable=True,
            is_subscriber_only=False,
        )
        for index, (artist, profile_fields) in enumerate(extra_artists, start=1):
            self.upsert_music(
                artist=artist,
                title=f"{profile_fields['stage_name']} Demo {index}",
                genre=profile_fields["genre"],
                bpm=72 + (index * 7) % 68,
                is_downloadable=index % 3 == 0,
                is_subscriber_only=index % 4 == 0,
            )

        luna_post = self.upsert_post(
            author=artist_luna,
            title="First supporter demo",
            body="Testing a supporter-first update with behind-the-scenes notes for the next single.",
            post_type=Post.TEXT,
            is_subscriber_only=False,
            comment_mode=Post.COMMENT_SUBSCRIBERS,
        )
        self.upsert_post(
            author=artist_luna,
            title="Private demo clip",
            body="A rough chorus idea for supporters before it becomes a proper release.",
            post_type=Post.MUSIC,
            is_subscriber_only=True,
            comment_mode=Post.COMMENT_SUBSCRIBERS,
        )
        self.upsert_post(
            author=artist_luna,
            profession=ArtistProfile.VISUAL_ART,
            title="Watercolour study preview",
            body="Testing the arts side with a small watercolour process note for collectors and supporters.",
            post_type=Post.TEXT,
            is_subscriber_only=False,
            comment_mode=Post.COMMENT_SUBSCRIBERS,
        )
        self.upsert_post(
            author=artist_static,
            title="Live room test this Friday",
            body="Trying a short live set with one unreleased track and a Q&A after.",
            post_type=Post.LIVE,
            is_subscriber_only=False,
            comment_mode=Post.COMMENT_ANYONE,
        )
        for artist, profile_fields in extra_artists[:8]:
            self.upsert_post(
                author=artist,
                title="New demo notes",
                body=f"Working through a new {profile_fields['genre']} idea and testing how it lands with early listeners.",
                post_type=Post.TEXT,
                is_subscriber_only=False,
                comment_mode=Post.COMMENT_SUBSCRIBERS,
            )

        Comment.objects.get_or_create(
            post=luna_post,
            author=fan,
            body="This direction sounds great. The chorus note is working.",
        )
        Like.objects.get_or_create(post=luna_post, user=fan)

        self.upsert_product(
            artist=artist_luna,
            product_type=Product.MERCH,
            title="Luna Lane Logo Tee",
            description="Soft black tee from the demo storefront.",
            price=Decimal("28.00"),
            stock_quantity=25,
            sizes="S,M,L,XL",
            shipping_required=True,
        )
        self.upsert_product(
            artist=artist_luna,
            profession=ArtistProfile.VISUAL_ART,
            product_type=Product.EXTERNAL_FULFILLMENT,
            title="Luna Lane Watercolour Print",
            description="Demo arts-side print listing. Supporting music does not unlock arts-side supporter items.",
            price=Decimal("45.00"),
            external_url="https://artist-shop.example.com/luna-watercolour-print",
            external_discount_code="ARTSUPPORT10",
        )
        self.upsert_product(
            artist=artist_static,
            product_type=Product.BEAT,
            title="Low Tide Beat License",
            description="Non-exclusive beat license with preview access.",
            price=Decimal("19.00"),
            bpm=78,
            music_key="F minor",
            license_type="Non-exclusive",
        )
        self.upsert_product(
            artist=artist_luna,
            product_type=Product.SAMPLE_PACK,
            title="Paper Moons Vocal Chops",
            description="Supporter-only vocal chop sample pack placeholder.",
            price=Decimal("7.00"),
            is_supporter_only=True,
        )
        for index, (artist, profile_fields) in enumerate(extra_artists[:6], start=1):
            self.upsert_product(
                artist=artist,
                product_type=Product.SAMPLE_PACK if index % 2 else Product.BEAT,
                title=f"{profile_fields['stage_name']} Starter Pack",
                description=f"Demo store item for {profile_fields['genre']} fans.",
                price=Decimal("5.00") + Decimal(index),
                bpm=90 + index,
                license_type="Demo license",
            )

        self.seed_products_for_artists(artist_users)
        host_count = self.seed_bulk_hosts(artist_users)
        self.seed_beta_team()
        call_command("beta_scene_loop", seed_only=True)

        User.objects.filter(username="fan_newcomer").update(session_login_count=1)
        User.objects.filter(username="demo_fan").update(session_login_count=2)
        User.objects.filter(username="fan_power_user").update(session_login_count=10)
        User.objects.filter(username="luna_lane").update(session_login_count=3)
        User.objects.filter(username="team_host").update(session_login_count=2)

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
        self.stdout.write(
            f"Bulk scene: {len(bulk_artists)} artists, {len(bulk_fans)} fans, {host_count} host spaces "
            f"across {', '.join(BULK_CITIES)}."
        )
        self.stdout.write("Fan logins include: demo_fan, fan_indie_mel, fan_rnb_syd, fan_newcomer, fan_power_user / demo12345")
        self.stdout.write("Bulk fan logins: scene_fan_001 … scene_fan_200 / demo12345")
        self.stdout.write("Artist logins include: luna_lane, static_harbor, mika_north, river_kite, velvet_parade / demo12345")
        self.stdout.write("Bulk artist logins: scene_artist_mel_01, scene_artist_syd_01, scene_artist_bri_01 / demo12345")
        self.stdout.write("Bulk host logins: scene_host_001 … scene_host_040 / demo12345")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Beta team of 7 (password demo12345 for all):"))
        self.stdout.write("  team_fan          — Fan tester (Melbourne, clean discover)")
        self.stdout.write("  team_artist       — Artist tester (upload, post, store)")
        self.stdout.write("  team_host         — Host tester (listings + booking inbox)")
        self.stdout.write("  team_fan_sydney   — Second fan (Sydney cross-city)")
        self.stdout.write("  team_artist_sydney — Second artist (Sydney gigs)")
        self.stdout.write("  team_promoter     — Promotions tester (Discovery Ads)")
        self.stdout.write("  team_admin        — Admin (beta feedback triage in Profile)")
        self.stdout.write("")
        self.stdout.write("Legacy demo accounts still work: demo_fan, luna_lane, beta_host_cafe, marlo_saints")

        launch_city = (options.get("launch_city") or "").strip()
        if launch_city:
            self.report_launch_city(launch_city)

    def report_launch_city(self, city):
        city_label = city.strip()
        artist_count = ArtistProfile.objects.filter(city__iexact=city_label).count()
        host_count = HostProfile.objects.filter(city__iexact=city_label).count()
        listing_count = SpaceListing.objects.filter(city__iexact=city_label, status="live").count()
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Launch city snapshot: {city_label}"))
        self.stdout.write(f"  Artists with profiles in {city_label}: {artist_count}")
        self.stdout.write(f"  Host profiles in {city_label}: {host_count}")
        self.stdout.write(f"  Live space listings in {city_label}: {listing_count}")
        self.stdout.write("  Ops: run before early signup so creators see a living local scene.")
        self.stdout.write("  Example: python manage.py seed_demo --launch-city Melbourne")

    def seed_beta_team(self):
        """Six clean accounts for human beta testing — one role each, minimal pre-seeding."""
        from promotions.services import grant_credits

        team_fan = self.upsert_user(
            username="team_fan",
            password=DEMO_PASSWORD,
            user_type=User.FAN,
            display_name="Team Fan",
            favorite_genres="indie pop, alt R&B, bedroom pop",
            discovery_location="Melbourne",
            is_beta_tester=True,
            beta_notes="Beta team fan: discover, follow, subscribe, My Scene tickets.",
        )
        team_artist = self.upsert_user(
            username="team_artist",
            password=DEMO_PASSWORD,
            user_type=User.ARTIST,
            display_name="Team Artist",
            discovery_location="Melbourne",
            is_beta_tester=True,
            beta_notes="Beta team artist: upload, post, store, promote.",
        )
        team_host = self.upsert_user(
            username="team_host",
            password=DEMO_PASSWORD,
            user_type=User.HOST,
            display_name="Team Host",
            discovery_location="Melbourne",
            is_beta_tester=True,
            beta_notes="Beta team host: listings, booking requests, show night.",
        )
        team_fan_sydney = self.upsert_user(
            username="team_fan_sydney",
            password=DEMO_PASSWORD,
            user_type=User.FAN,
            display_name="Team Fan Sydney",
            favorite_genres="dream pop, synth pop, indie rock",
            discovery_location="Sydney",
            is_beta_tester=True,
            beta_notes="Beta team fan #2: cross-city discovery and saved artists.",
        )
        team_artist_sydney = self.upsert_user(
            username="team_artist_sydney",
            password=DEMO_PASSWORD,
            user_type=User.ARTIST,
            display_name="Team Artist Sydney",
            discovery_location="Sydney",
            is_beta_tester=True,
            beta_notes="Beta team artist #2: Sydney gigs and fan growth.",
        )
        team_promoter = self.upsert_user(
            username="team_promoter",
            password=DEMO_PASSWORD,
            user_type=User.ARTIST,
            display_name="Team Promoter",
            discovery_location="Melbourne",
            artist_plan="studio",
            is_beta_tester=True,
            beta_notes="Beta team promoter: Discovery Ads campaigns and analytics.",
        )
        self.upsert_user(
            username="team_admin",
            password=DEMO_PASSWORD,
            user_type=User.ADMIN,
            display_name="Team Admin",
            is_staff=True,
            is_beta_tester=True,
            beta_notes="Beta team admin: review and triage beta feedback from Profile.",
        )

        self.upsert_artist_profile(
            team_artist,
            stage_name="Team Artist",
            genre="Indie Pop",
            city="Melbourne",
            artist_story="Fresh Melbourne act for the beta team to follow, support, and see live.",
            influences="Clairo, BENEE, The Japanese House",
            is_verified=False,
        )
        self.upsert_artist_profile(
            team_artist_sydney,
            stage_name="Team Artist Sydney",
            genre="Dream Pop",
            city="Sydney",
            artist_story="Sydney-side artist for cross-city discovery and venue booking tests.",
            influences="Beach House, Hatchie",
        )
        self.upsert_artist_profile(
            team_promoter,
            stage_name="Team Promoter",
            genre="Alt R&B",
            city="Melbourne",
            artist_story="Artist running Discovery Ads campaigns during beta.",
            influences="Frank Ocean, Dijon",
        )

        HostProfile.objects.update_or_create(
            user=team_host,
            defaults={
                "business_name": "Team Venue Melbourne",
                "contact_email": "team_host@indiefund.local",
                "address": "88 Beta Lane",
                "city": "Melbourne",
                "verified": True,
            },
        )
        team_listing, _ = SpaceListing.objects.update_or_create(
            host=team_host,
            name="Team Venue — Beta Room",
            defaults={
                "description": "Intimate room for the beta team show loop — PA, bar, 35 seats.",
                "address": "88 Beta Lane, Melbourne",
                "city": "Melbourne",
                "capacity": 35,
                "available_windows": [{"day": "sat", "start": "19:00", "end": "23:00"}],
                "tags": ["indie", "beta", "melbourne"],
                "bar_open": True,
                "kitchen_open": False,
                "drink_minimum": "One drink minimum",
                "split_type": SpaceListing.DOOR_PERCENT,
                "host_cut_percent": 15,
                "booking_mode": SpaceListing.REQUEST,
                "min_local_supporters": 0,
                "status": SpaceListing.LIVE,
            },
        )
        ensure_listing_gallery(team_listing)

        for artist, title, genre in (
            (team_artist, "Beta Room Demo", "Indie Pop"),
            (team_artist_sydney, "Harbour Lights Demo", "Dream Pop"),
            (team_promoter, "Promo Track One", "Alt R&B"),
        ):
            self.upsert_music(
                artist=artist,
                title=title,
                genre=genre,
                bpm=102,
                is_downloadable=True,
                is_subscriber_only=False,
            )

        for artist, body in (
            (team_artist, "First beta-team post — testing updates and fan notifications."),
            (team_promoter, "Launch week promo — running a Discovery Ads campaign this week."),
        ):
            self.upsert_post(
                author=artist,
                title="Beta team update",
                body=body,
                post_type=Post.TEXT,
                is_subscriber_only=False,
                comment_mode=Post.COMMENT_ANYONE,
            )

        self.upsert_product(
            artist=team_artist,
            product_type=Product.MERCH,
            title="Team Artist Tee",
            description="Demo tee for beta checkout flows.",
            price=Decimal("24.00"),
            stock_quantity=15,
            sizes="S,M,L,XL",
            shipping_required=True,
        )

        ArtistFollow.objects.get_or_create(fan=team_fan, artist=team_artist)
        FanSubscription.objects.update_or_create(
            fan=team_fan,
            artist=team_artist,
            defaults={
                "monthly_amount": Decimal("3.00"),
                "billing_date": 1,
                "active": True,
                "payment_provider": "demo",
                "stripe_status": "active",
            },
        )
        ArtistFollow.objects.get_or_create(fan=team_fan_sydney, artist=team_artist_sydney)

        starts_at = timezone.now() + timedelta(days=10)
        ends_at = starts_at + timedelta(hours=2)
        SpaceBooking.objects.update_or_create(
            listing=team_listing,
            artist=team_artist,
            status=SpaceBooking.CONFIRMED,
            defaults={
                "starts_at": starts_at,
                "ends_at": ends_at,
                "expected_audience": 30,
                "pitch": "Beta team showcase — Team Artist live at Team Venue.",
            },
        )

        grant_credits(team_promoter, Decimal("50.00"), description="Beta team promotion credits")

    def upsert_user(self, username, password, user_type, display_name, **fields):
        user, created = User.objects.get_or_create(
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

    def upsert_artist_profile(self, owner, **fields):
        profile, _ = ArtistProfile.objects.update_or_create(
            owner=owner,
            defaults=fields,
        )
        return profile

    def upsert_music(self, artist, title, **fields):
        track, created = MusicUpload.objects.update_or_create(
            artist=artist,
            title=title,
            defaults=fields,
        )
        if created or not track.audio_file or str(track.audio_file.name).endswith(".mp3"):
            track.audio_file.save(
                f"{artist.username}-{title.lower().replace(' ', '-')}.wav",
                ContentFile(self.create_demo_wav(fields.get("bpm") or 96)),
                save=True,
            )
        if created or not track.cover_art:
            track.cover_art.save(
                f"{artist.username}-{title.lower().replace(' ', '-')}.png",
                ContentFile(self.create_cover_png(artist.display_name or artist.username, fields.get("genre", ""))),
                save=True,
            )
        return track

    def create_demo_wav(self, bpm):
        key = int(bpm or 96)
        if key not in self._demo_wav_cache:
            self._demo_wav_cache[key] = self._build_demo_wav(key)
        return self._demo_wav_cache[key]

    def _build_demo_wav(self, bpm):
        sample_rate = 22050
        duration = 4
        frequency = 220 + (int(bpm) % 48) * 5
        buffer = io.BytesIO()

        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            frames = bytearray()
            for index in range(sample_rate * duration):
                beat = 1.0 if (index % max(1, int(sample_rate * 60 / max(int(bpm), 1)))) < 900 else 0.42
                envelope = min(1, index / 2000) * min(1, (sample_rate * duration - index) / 3000)
                sample = int(18000 * envelope * beat * math.sin(2 * math.pi * frequency * index / sample_rate))
                frames.extend(sample.to_bytes(2, byteorder="little", signed=True))

            wav_file.writeframes(bytes(frames))

        return buffer.getvalue()

    def create_cover_png(self, artist_name, genre):
        key = (artist_name, genre or "")
        if key not in self._cover_png_cache:
            self._cover_png_cache[key] = self._build_cover_png(artist_name, genre)
        return self._cover_png_cache[key]

    def _build_cover_png(self, artist_name, genre):
        palette = [
            ((168, 85, 247), (34, 197, 94)),
            ((14, 165, 233), (236, 72, 153)),
            ((245, 158, 11), (99, 102, 241)),
            ((16, 185, 129), (244, 63, 94)),
        ]
        first = sum(ord(char) for char in artist_name) % len(palette)
        color_a, color_b = palette[first]
        image = Image.new("RGB", (800, 800), color_a)
        draw = ImageDraw.Draw(image)

        for y in range(800):
            ratio = y / 799
            color = tuple(int(color_a[i] * (1 - ratio) + color_b[i] * ratio) for i in range(3))
            draw.line([(0, y), (800, y)], fill=color)

        initials = "".join(part[0] for part in artist_name.split()[:2]).upper()
        try:
            font_large = ImageFont.truetype("Arial.ttf", 150)
            font_small = ImageFont.truetype("Arial.ttf", 34)
        except OSError:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

        draw.rounded_rectangle((90, 250, 710, 550), radius=48, fill=(0, 0, 0, 90), outline=(255, 255, 255), width=4)
        draw.text((400, 350), initials, fill=(255, 255, 255), font=font_large, anchor="mm")
        draw.text((400, 488), genre or "Demo Preview", fill=(255, 255, 255), font=font_small, anchor="mm")

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def upsert_post(self, author, title, **fields):
        post, _ = Post.objects.update_or_create(
            author=author,
            title=title,
            defaults=fields,
        )
        return post

    def upsert_product(self, artist, title, **fields):
        product, _ = Product.objects.update_or_create(
            artist=artist,
            title=title,
            defaults=fields,
        )
        return product

    def beta_notes_for(self, username):
        notes = {
            "fan_indie_mel": "Fan beta tester: start with discovery, save artists, then report whether recommendations feel relevant.",
            "fan_rnb_syd": "Fan beta tester: verify location filtering, support checkout messaging and subscriber-only access.",
            "fan_beatmaker_bri": "Fan beta tester: focus on marketplace previews, beats, sample packs and download clarity.",
            "fan_folk_ade": "Fan beta tester: test saved artist filtering and whether artist profile stories are easy to find.",
            "fan_newcomer": "New-user beta tester: register/login, empty states and onboarding should be understandable without demo history.",
            "fan_power_user": "Power beta tester: test dense states with saved artists, active subscriptions and notifications.",
            "fan_mobile_first": "Mobile beta tester: verify bottom navigation, profile preferences and external social link behavior.",
            "fan_subscriber": "Subscriber beta tester: verify supporter-only music, posts and support management messaging.",
        }
        return notes.get(username, "Beta tester: report confusing account setup or navigation moments.")

    def seed_beta_feedback(self, fans, artists):
        feedback_rows = [
            (fans[0], "navigation", "medium", "/?page=saved", "Saved artists need clearer next steps", "After saving artists, prompt fans to follow, support, or play music from the saved screen."),
            (fans[1], "setup", "high", "/?page=profile", "Fan onboarding should explain discovery preferences", "Favorite genres and location affect recommendations, but the setup form does not explain that yet."),
            (fans[4], "setup", "medium", "/?page=profile", "Empty newcomer account needs a checklist", "A brand-new fan lands in empty states and needs a short path through discovery, save, support and notifications."),
            (fans[6], "navigation", "high", "/?page=discover", "Mobile tester wants clearer active nav state", "On a narrow screen, make it obvious whether the fan is in Home, Discover, Saved or Profile."),
            (artists[0], "content", "medium", "/?artist=luna_lane", "Artist dashboard needs launch checklist", "Artists need to know whether profile, music, posts, store and live tabs are complete enough to publish."),
            (artists[1], "payments", "high", "/?artist=static_harbor", "Support management copy needs production path", "The demo billing fallback is useful, but beta testers need a clear note when Stripe is not configured."),
        ]

        for user, category, severity, path, summary, details in feedback_rows:
            BetaFeedback.objects.update_or_create(
                user=user,
                summary=summary,
                defaults={
                    "category": category,
                    "severity": severity,
                    "path": path,
                    "details": details,
                },
            )

    def seed_fan_relationships(self, fans, artists):
        for fan_index, fan in enumerate(fans):
            if fan.user_type != User.FAN:
                continue

            if fan.username == "demo_fan":
                mel_artists = [
                    artist for artist in artists
                    if getattr(getattr(artist, "artist_profile", None), "city", "") == "Melbourne"
                ]
                saved_artists = (mel_artists[:2] if mel_artists else artists[:2]) + artists
            else:
                saved_artists = artists[fan_index % len(artists):] + artists[:fan_index % len(artists)]

            seen = set()
            saved_artists = [
                artist for artist in saved_artists
                if not (artist.id in seen or seen.add(artist.id))
            ]
            for artist in saved_artists[:4]:
                if fan == artist:
                    continue
                ArtistFollow.objects.get_or_create(fan=fan, artist=artist)
                ArtistSignal.objects.update_or_create(
                    fan=fan,
                    artist=artist,
                    signal_type=ArtistSignal.SAVE,
                    defaults={
                        "liked_genre": getattr(artist.artist_profile, "genre", ""),
                        "weight": 1.4,
                        "reason": "Demo saved artist",
                    },
                )

            for artist in saved_artists[4:6]:
                ArtistSignal.objects.update_or_create(
                    fan=fan,
                    artist=artist,
                    signal_type=ArtistSignal.MORE_LIKE_THIS,
                    defaults={
                        "liked_genre": getattr(artist.artist_profile, "genre", ""),
                        "weight": 1.2,
                        "reason": "Demo more-like-this artist",
                    },
                )

            if len(saved_artists) > 6:
                ArtistSignal.objects.update_or_create(
                    fan=fan,
                    artist=saved_artists[6],
                    signal_type=ArtistSignal.SKIP,
                    defaults={
                        "liked_genre": getattr(saved_artists[6].artist_profile, "genre", ""),
                        "weight": -1.0,
                        "reason": "Demo skipped artist",
                    },
                )

            for sub_offset, artist in enumerate(saved_artists[:2]):
                monthly_amount = Decimal("1.00") + Decimal((fan_index + sub_offset) % 5)
                if fan.username == "demo_fan" and sub_offset == 0:
                    monthly_amount = Decimal("3.00")
                FanSubscription.objects.update_or_create(
                    fan=fan,
                    artist=artist,
                    defaults={
                        "monthly_amount": monthly_amount,
                        "billing_date": ((fan_index + sub_offset) % 28) + 1,
                        "active": True,
                        "payment_provider": "demo",
                        "stripe_status": "active",
                    },
                )

            Notification.objects.update_or_create(
                recipient=fan,
                actor=saved_artists[0],
                notification_type=Notification.POST,
                title=f"{saved_artists[0].display_name or saved_artists[0].username} posted a demo update",
                defaults={
                    "body": "Seeded notification for testing the fan notifications navigation.",
                    "target_url": f"/?artist={saved_artists[0].username}",
                },
            )
            Notification.objects.update_or_create(
                recipient=saved_artists[0],
                actor=fan,
                notification_type=Notification.SUPPORTER,
                title=f"{fan.display_name or fan.username} is supporting you",
                defaults={
                    "body": "Seeded notification for testing artist supporter activity.",
                    "target_url": "/?page=profile",
                },
            )

    def seed_bulk_artists(self):
        genres = [
            "Indie Pop", "Alt R&B", "Dream Pop", "Electronic", "Indie Folk",
            "Bedroom Pop", "Indie Rock", "Soul", "Synth Pop", "Psych Pop",
        ]
        artists = []
        per_city = math.ceil(BULK_ARTIST_COUNT / len(BULK_CITIES))
        city_codes = {"Melbourne": "mel", "Sydney": "syd", "Brisbane": "bri"}

        for index in range(BULK_ARTIST_COUNT):
            city = BULK_CITIES[index // per_city]
            city_code = city_codes[city]
            slot = (index % per_city) + 1
            genre = genres[index % len(genres)]
            stage_name = f"Scene {city.split()[0]} {slot:02d}"
            username = f"scene_artist_{city_code}_{slot:02d}"
            artist = self.upsert_user(
                username=username,
                password=DEMO_PASSWORD,
                user_type=User.ARTIST,
                display_name=stage_name,
                is_beta_tester=True,
                beta_notes=f"Bulk scene artist in {city}: verify discovery, store, and gig booking density.",
            )
            self.upsert_artist_profile(
                artist,
                stage_name=stage_name,
                genre=genre,
                city=city,
                artist_story=f"Seeded {genre.lower()} artist for beta load testing in {city}.",
                influences="Demo seed only",
            )
            self.upsert_music(
                artist=artist,
                title=f"{stage_name} Single",
                genre=genre,
                bpm=80 + (index * 5) % 60,
                is_downloadable=index % 2 == 0,
                is_subscriber_only=index % 5 == 0,
            )
            if index % 3 == 0:
                self.upsert_post(
                    author=artist,
                    title=f"{stage_name} studio update",
                    body=f"Testing {genre} posts and fan notifications from the bulk scene seed.",
                    post_type=Post.TEXT,
                    is_subscriber_only=False,
                    comment_mode=Post.COMMENT_SUBSCRIBERS,
                )
            artists.append(artist)
        return artists

    def seed_bulk_fans(self):
        genre_pools = {
            "Melbourne": "indie pop, alt R&B, soul, bedroom pop",
            "Sydney": "dream pop, synth pop, electronic, indie rock",
            "Brisbane": "electronic, psych pop, indie folk, sample packs",
        }
        fans = []
        for index in range(1, BULK_FAN_COUNT + 1):
            city = BULK_CITIES[(index - 1) % len(BULK_CITIES)]
            fan = self.upsert_user(
                username=f"scene_fan_{index:03d}",
                password=DEMO_PASSWORD,
                user_type=User.FAN,
                display_name=f"Scene Fan {index:03d}",
                favorite_genres=genre_pools[city],
                discovery_location=city,
                email=f"scene_fan_{index:03d}@indiefund.local",
                is_beta_tester=index <= 12,
                beta_notes="Bulk scene fan: discovery, support, and local show engagement.",
            )
            fans.append(fan)
        return fans

    def seed_bulk_fan_engagement(self, fans, artists):
        if not fans or not artists:
            return

        artists_by_city = {city: [] for city in BULK_CITIES}
        for artist in artists:
            try:
                city = artist.artist_profile.city
            except ArtistProfile.DoesNotExist:
                continue
            if city in artists_by_city:
                artists_by_city[city].append(artist)
            else:
                artists_by_city[BULK_CITIES[0]].append(artist)

        follows = []
        signals = []
        subscriptions = []

        for fan_index, fan in enumerate(fans):
            pool = artists_by_city.get(fan.discovery_location) or artists
            if not pool:
                pool = artists

            saved_artists = []
            for offset in range(4):
                saved_artists.append(pool[(fan_index + offset) % len(pool)])

            for artist in saved_artists:
                follows.append(ArtistFollow(fan=fan, artist=artist))
                try:
                    genre = artist.artist_profile.genre
                except ArtistProfile.DoesNotExist:
                    genre = ""
                signals.append(ArtistSignal(
                    fan=fan,
                    artist=artist,
                    signal_type=ArtistSignal.SAVE,
                    liked_genre=genre,
                    weight=1.3,
                    reason="Bulk scene saved artist",
                ))

            more_like = pool[(fan_index + 4) % len(pool)]
            try:
                genre = more_like.artist_profile.genre
            except ArtistProfile.DoesNotExist:
                genre = ""
            signals.append(ArtistSignal(
                fan=fan,
                artist=more_like,
                signal_type=ArtistSignal.MORE_LIKE_THIS,
                liked_genre=genre,
                weight=1.1,
                reason="Bulk scene more-like-this",
            ))

            for sub_offset, artist in enumerate(saved_artists[:2]):
                subscriptions.append(FanSubscription(
                    fan=fan,
                    artist=artist,
                    monthly_amount=Decimal("1.00") + Decimal((fan_index + sub_offset) % 4),
                    billing_date=((fan_index + sub_offset) % 28) + 1,
                    active=True,
                    payment_provider="demo",
                    stripe_status="active",
                ))

        ArtistFollow.objects.bulk_create(follows, ignore_conflicts=True)
        ArtistSignal.objects.bulk_create(signals, ignore_conflicts=True)
        FanSubscription.objects.bulk_create(subscriptions, ignore_conflicts=True)

    def seed_products_for_artists(self, artists):
        templates = [
            {
                "suffix": "Logo Tee",
                "product_type": Product.MERCH,
                "description": "Soft tee from the demo storefront.",
                "price": Decimal("28.00"),
                "extra": {
                    "stock_quantity": 20,
                    "sizes": "S,M,L,XL",
                    "shipping_required": True,
                },
            },
            {
                "suffix": "Sample Pack",
                "product_type": Product.SAMPLE_PACK,
                "description": "Demo loops and one-shots for supporters.",
                "price": Decimal("9.00"),
                "extra": {"license_type": "Demo license"},
            },
            {
                "suffix": "Digital EP",
                "product_type": Product.DIGITAL_DOWNLOAD,
                "description": "Name-your-price digital download placeholder.",
                "price": Decimal("6.00"),
                "extra": {},
            },
        ]

        for artist in artists:
            try:
                profile = artist.artist_profile
            except ArtistProfile.DoesNotExist:
                continue

            existing = Product.objects.filter(artist=artist).count()
            if existing >= len(templates):
                continue

            for template in templates[existing:]:
                self.upsert_product(
                    artist=artist,
                    product_type=template["product_type"],
                    title=f"{profile.stage_name} {template['suffix']}",
                    description=template["description"],
                    price=template["price"],
                    **template["extra"],
                )

    def seed_bulk_hosts(self, artists):
        venue_names = [
            "Harbour Room", "Back Alley Stage", "Rooftop Sessions", "Basement Radio",
            "Garden Amp", "Laneway Loft", "River Stage", "Neon Parlour", "Tape Room",
            "Corner Studio",
        ]
        artists_by_city = {city: [] for city in BULK_CITIES}
        for artist in artists:
            try:
                city = artist.artist_profile.city
            except ArtistProfile.DoesNotExist:
                continue
            if city in artists_by_city:
                artists_by_city[city].append(artist)
            else:
                artists_by_city[BULK_CITIES[0]].append(artist)

        created = 0
        for index in range(1, BULK_HOST_COUNT + 1):
            city = BULK_CITIES[(index - 1) % len(BULK_CITIES)]
            venue = venue_names[(index - 1) % len(venue_names)]
            username = f"scene_host_{index:03d}"
            host = self.upsert_user(
                username=username,
                password=DEMO_PASSWORD,
                user_type=User.HOST,
                display_name=f"{venue} Host",
                discovery_location=city,
                email=f"{username}@indiefund.local",
                is_beta_tester=index <= 5,
                beta_notes=f"Bulk scene host in {city}: verify listings, bookings, and Spaces inbox.",
            )
            HostProfile.objects.update_or_create(
                user=host,
                defaults={
                    "business_name": f"{venue} {city}",
                    "contact_email": f"{username}@indiefund.local",
                    "address": f"{index + 10} Demo Street",
                    "city": city,
                    "verified": index % 4 != 0,
                },
            )
            listing, _ = SpaceListing.objects.update_or_create(
                host=host,
                name=f"{venue} — {city}",
                defaults={
                    "description": f"Seeded {city} venue with PA, bar, and {30 + (index % 40)} seats.",
                    "address": f"{index + 10} Demo Street, {city}",
                    "city": city,
                    "capacity": 30 + (index % 40),
                    "available_windows": [{"day": "fri", "start": "19:00", "end": "23:00"}],
                    "tags": ["indie", "live", city.lower()],
                    "bar_open": True,
                    "kitchen_open": index % 3 == 0,
                    "drink_minimum": "One drink minimum",
                    "split_type": SpaceListing.DOOR_PERCENT,
                    "host_cut_percent": 15 + (index % 10),
                    "booking_mode": SpaceListing.REQUEST if index % 5 else SpaceListing.INSTANT_BOOK,
                    "min_local_supporters": 2 if index % 2 else 0,
                    "status": SpaceListing.LIVE,
                },
            )
            ensure_listing_gallery(listing)

            artist_pool = artists_by_city.get(city) or artists
            artist = artist_pool[(index - 1) % len(artist_pool)]
            starts_at = timezone.now() + timedelta(days=3 + (index % 21), hours=(index % 6))
            ends_at = starts_at + timedelta(hours=2)
            SpaceBooking.objects.update_or_create(
                listing=listing,
                artist=artist,
                status=SpaceBooking.CONFIRMED,
                defaults={
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                    "expected_audience": 25 + (index % 30),
                    "pitch": f"Bulk scene booking — {artist.display_name or artist.username} live at {venue}.",
                },
            )
            created += 1
        return created
