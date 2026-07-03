from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from artists.models import ArtistProfile


User = get_user_model()


class PublicArtistMetaTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="public_artist",
            password="password123",
            user_type=User.ARTIST,
        )
        ArtistProfile.objects.create(
            owner=self.artist,
            stage_name="Public Artist",
            genre="Indie",
            city="Melbourne",
            artist_story="Support direct.",
        )

    def test_public_artist_meta_returns_seo_fields(self):
        response = self.client.get("/api/artists/public/public_artist/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["stage_name"], "Public Artist")
        self.assertIn("artist=public_artist", response.data["page_url"])
        self.assertIn("Public Artist", response.data["title"])

    def test_public_artist_meta_honors_profession_query(self):
        profile = ArtistProfile.objects.get(owner=self.artist)
        profile.professions = "music,comedy"
        profile.save(update_fields=["professions"])
        profile.profession_profiles.create(
            profession=ArtistProfile.COMEDY,
            display_title="Stand-up Side",
            bio="Club sets and specials.",
            style="Stand-up",
        )

        response = self.client.get("/api/artists/public/public_artist/?profession=comedy")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["profession"], "comedy")
        self.assertEqual(response.data["display_title"], "Stand-up Side")
        self.assertIn("profession=comedy", response.data["page_url"])
        self.assertIn("Comedian", response.data["title"])

    @override_settings(PLATFORM_MODE="live")
    def test_robots_and_sitemap_available(self):
        robots = self.client.get("/robots.txt")
        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(robots.status_code, 200)
        self.assertIn("Sitemap:", robots.content.decode())
        self.assertEqual(sitemap.status_code, 200)
        self.assertIn("public_artist", sitemap.content.decode())
