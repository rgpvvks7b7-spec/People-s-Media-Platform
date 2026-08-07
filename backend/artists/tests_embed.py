from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from artists.models import ArtistProfile


User = get_user_model()


class ArtistEmbedTests(APITestCase):
    def setUp(self):
        self.artist = User.objects.create_user(
            username="embed_artist",
            password="password123",
            user_type=User.ARTIST,
            display_name="Embed Artist",
        )
        ArtistProfile.objects.create(
            owner=self.artist,
            stage_name="Embed Artist",
            genre="dream pop",
            city="Melbourne",
            artist_story="Late-night songs for city trains.",
        )

    def test_embed_returns_html_widget_and_allows_framing(self):
        response = self.client.get("/api/artists/public/embed_artist/embed/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response["Content-Type"])
        body = response.content.decode()
        self.assertIn("Embed Artist", body)
        self.assertIn("Support on IndieFund", body)
        self.assertIn("artist=embed_artist", body)
        self.assertNotIn("X-Frame-Options", response)
        self.assertEqual(response["Content-Security-Policy"], "frame-ancestors *")

    def test_embed_404_for_unknown_artist(self):
        response = self.client.get("/api/artists/public/missing/embed/")
        self.assertEqual(response.status_code, 404)
