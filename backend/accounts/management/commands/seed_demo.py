import io
import math
import wave
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFont

from artists.models import ArtistFollow, ArtistProfile
from marketplace.models import Product
from mediahub.models import MusicUpload
from posts.models import Comment, Like, Post
from subscriptions.models import FanSubscription


User = get_user_model()


class Command(BaseCommand):
    help = "Seed local demo users, artists, posts, music, products, and subscriptions."

    def handle(self, *args, **options):
        fan = self.upsert_user(
            username="demo_fan",
            password="demo12345",
            user_type=User.FAN,
            display_name="Demo Fan",
            favorite_genres="indie pop, alt R&B, bedroom pop",
            discovery_location="Melbourne",
        )

        artist_luna = self.upsert_user(
            username="luna_lane",
            password="demo12345",
            user_type=User.ARTIST,
            display_name="Luna Lane",
        )
        artist_static = self.upsert_user(
            username="static_harbor",
            password="demo12345",
            user_type=User.ARTIST,
            display_name="Static Harbor",
        )
        artist_mika = self.upsert_user(
            username="mika_north",
            password="demo12345",
            user_type=User.ARTIST,
            display_name="Mika North",
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

        ArtistFollow.objects.get_or_create(fan=fan, artist=artist_luna)
        ArtistFollow.objects.get_or_create(fan=fan, artist=artist_static)

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
            comment_mode=Post.COMMENT_FOLLOWERS,
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
                comment_mode=Post.COMMENT_FOLLOWERS,
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

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
        self.stdout.write("Fan login: demo_fan / demo12345")
        self.stdout.write("Artist logins include: luna_lane, static_harbor, mika_north, river_kite, velvet_parade / demo12345")

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
