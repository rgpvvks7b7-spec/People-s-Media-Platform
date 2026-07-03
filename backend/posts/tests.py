from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from artists.models import ArtistFanContact, ArtistFollow, ArtistProfile
from notifications.models import Notification
from posts.models import Comment, Instant, InstantReport, Like, PointOfView, Post
from subscriptions.models import FanSubscription


User = get_user_model()


class PostAccessTests(APITestCase):
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
        self.supporter = User.objects.create_user(
            username="supporter",
            password="password123",
            user_type=User.FAN,
        )
        ArtistProfile.objects.create(
            owner=self.artist,
            stage_name="Artist",
            comment_mode=ArtistProfile.COMMENT_SUBSCRIBERS,
            professions="music,visual_art",
        )
        self.public_post = Post.objects.create(
            author=self.artist,
            title="Public",
            comment_mode=Post.COMMENT_ANYONE,
        )
        self.supporter_post = Post.objects.create(
            author=self.artist,
            title="Supporters",
            is_subscriber_only=True,
            comment_mode=Post.COMMENT_SUBSCRIBERS,
            file="posts/private.mp3",
        )

    def test_supporter_only_posts_are_hidden_from_anonymous_and_visible_to_supporters(self):
        anonymous_response = self.client.get("/api/posts/")

        FanSubscription.objects.create(fan=self.supporter, artist=self.artist, active=True)
        self.client.force_authenticate(self.supporter)
        supporter_response = self.client.get("/api/posts/")

        anonymous_titles = {post["title"] for post in anonymous_response.data}
        supporter_titles = {post["title"] for post in supporter_response.data}
        supporter_private = next(post for post in supporter_response.data if post["title"] == "Supporters")

        self.assertNotIn("Supporters", anonymous_titles)
        self.assertIn("Supporters", supporter_titles)
        self.assertIn("/media/posts/private.mp3", supporter_private["file"])

    def test_inactive_subscription_does_not_unlock_supporter_only_posts(self):
        FanSubscription.objects.create(fan=self.supporter, artist=self.artist, active=False)
        self.client.force_authenticate(self.supporter)

        response = self.client.get("/api/posts/")
        titles = {post["title"] for post in response.data}

        self.assertNotIn("Supporters", titles)

    def test_support_for_other_profession_does_not_unlock_supporter_only_post(self):
        FanSubscription.objects.create(fan=self.supporter, artist=self.artist, profession="visual_art", active=True)
        self.client.force_authenticate(self.supporter)

        response = self.client.get("/api/posts/")
        titles = {post["title"] for post in response.data}

        self.assertNotIn("Supporters", titles)

    def test_fans_cannot_create_posts_but_artists_can(self):
        ArtistFanContact.objects.create(
            fan=self.fan,
            artist=self.artist,
            email_shared=True,
            source=ArtistFanContact.SUPPORT_PROMPT,
        )
        self.client.force_authenticate(self.fan)
        fan_response = self.client.post(
            "/api/posts/create/",
            {"title": "Fan Post", "body": "Nope"},
            format="multipart",
        )

        self.client.force_authenticate(self.artist)
        artist_response = self.client.post(
            "/api/posts/create/",
            {"title": "Artist Post", "body": "Yep"},
            format="multipart",
        )

        self.assertEqual(fan_response.status_code, 403)
        self.assertEqual(artist_response.status_code, 201)
        self.assertTrue(Post.objects.filter(title="Artist Post", author=self.artist).exists())
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.fan,
                actor=self.artist,
                notification_type=Notification.POST,
                title="New post: Artist Post",
            ).exists()
        )

    def test_artist_can_create_tiktok_embed_post(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/posts/create/",
            {
                "title": "Studio clip",
                "post_type": Post.TIKTOK,
                "external_url": "https://www.tiktok.com/@artist/video/1234567890",
            },
            format="multipart",
        )

        post = Post.objects.get(title="Studio clip")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(post.external_provider, Post.TIKTOK)
        self.assertEqual(post.external_url, "https://www.tiktok.com/@artist/video/1234567890")

    def test_social_embed_post_type_is_inferred_from_url(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/posts/create/",
            {
                "title": "Pasted clip",
                "external_url": "https://www.instagram.com/p/example",
            },
            format="multipart",
        )

        post = Post.objects.get(title="Pasted clip")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(post.post_type, Post.INSTAGRAM)
        self.assertEqual(post.external_provider, Post.INSTAGRAM)

    def test_social_embed_post_type_must_match_url_provider(self):
        self.client.force_authenticate(self.artist)

        response = self.client.post(
            "/api/posts/create/",
            {
                "title": "Wrong provider",
                "post_type": Post.INSTAGRAM,
                "external_url": "https://www.tiktok.com/@artist/video/1234567890",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Post.objects.filter(title="Wrong provider").exists())

    def test_comment_permissions_use_supporter_access_for_artist_settings(self):
        default_post = Post.objects.create(
            author=self.artist,
            title="Default Mode",
            comment_mode=Post.COMMENT_DEFAULT,
        )

        self.client.force_authenticate(self.fan)
        blocked_response = self.client.post(
            f"/api/posts/{default_post.id}/comment/",
            {"body": "Blocked"},
            format="json",
        )

        FanSubscription.objects.create(fan=self.fan, artist=self.artist, active=True)
        default_supporter_response = self.client.post(
            f"/api/posts/{default_post.id}/comment/",
            {"body": "Allowed"},
            format="json",
        )

        self.client.force_authenticate(self.supporter)
        supporter_blocked_response = self.client.post(
            f"/api/posts/{self.supporter_post.id}/comment/",
            {"body": "Not supporting"},
            format="json",
        )

        FanSubscription.objects.create(fan=self.supporter, artist=self.artist, active=True)
        private_supporter_response = self.client.post(
            f"/api/posts/{self.supporter_post.id}/comment/",
            {"body": "Supporting"},
            format="json",
        )

        self.assertEqual(blocked_response.status_code, 403)
        self.assertEqual(default_supporter_response.status_code, 201)
        self.assertEqual(supporter_blocked_response.status_code, 403)
        self.assertEqual(private_supporter_response.status_code, 201)
        self.assertEqual(Comment.objects.filter(post=default_post).count(), 1)
        self.assertEqual(Comment.objects.filter(post=self.supporter_post).count(), 1)

    def test_non_supporter_cannot_like_supporter_only_post_by_id(self):
        self.client.force_authenticate(self.fan)

        response = self.client.post(f"/api/posts/{self.supporter_post.id}/toggle-like/")

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Like.objects.filter(post=self.supporter_post, user=self.fan).exists())

    def test_artist_can_post_pov_and_profile_includes_latest_pinned(self):
        self.client.force_authenticate(self.artist)

        first_response = self.client.post(
            "/api/posts/pov/",
            {"body": "I make small songs for noisy rooms.", "profession": "music"},
            format="multipart",
        )
        second_response = self.client.post(
            "/api/posts/pov/",
            {"body": "Every release should feel handmade.", "profession": "music"},
            format="multipart",
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(PointOfView.objects.filter(artist=self.artist, profession="music", is_pinned=True).count(), 1)

        response = self.client.get("/api/artists/")
        artist_payload = next(item for item in response.data if item["owner_id"] == self.artist.id)
        self.assertEqual(artist_payload["pinned_pov"]["body"], "Every release should feel handmade.")

    def test_instants_filter_expired_and_gate_supporter_visibility(self):
        expired = Instant.objects.create(
            artist=self.artist,
            body="Gone",
            visibility=Instant.PUBLIC,
            expires_at=timezone.now() - timezone.timedelta(minutes=1),
        )
        public = Instant.objects.create(
            artist=self.artist,
            body="Public note",
            visibility=Instant.PUBLIC,
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        supporters = Instant.objects.create(
            artist=self.artist,
            body="Supporter note",
            visibility=Instant.SUPPORTERS,
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )

        anonymous_response = self.client.get("/api/posts/instants/")
        anonymous_bodies = {item["body"] for item in anonymous_response.data["results"]}

        FanSubscription.objects.create(fan=self.supporter, artist=self.artist, active=True)
        self.client.force_authenticate(self.supporter)
        supporter_response = self.client.get("/api/posts/instants/")
        supporter_bodies = [item["body"] for item in supporter_response.data["results"]]

        self.assertNotIn(expired.body, anonymous_bodies)
        self.assertIn(public.body, anonymous_bodies)
        self.assertNotIn(supporters.body, anonymous_bodies)
        self.assertEqual(supporter_bodies[0], supporters.body)
        self.assertIn(public.body, supporter_bodies)

    def test_follower_instants_are_visible_to_followers_only(self):
        instant = Instant.objects.create(
            artist=self.artist,
            body="Followers get the room note",
            visibility=Instant.FOLLOWERS,
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )

        self.client.force_authenticate(self.fan)
        blocked_response = self.client.get("/api/posts/instants/")
        ArtistFollow.objects.create(fan=self.fan, artist=self.artist)
        allowed_response = self.client.get("/api/posts/instants/")

        self.assertNotIn(instant.body, {item["body"] for item in blocked_response.data["results"]})
        self.assertIn(instant.body, {item["body"] for item in allowed_response.data["results"]})

    def test_artist_can_create_instant_and_fan_can_report_it(self):
        self.client.force_authenticate(self.artist)
        create_response = self.client.post(
            "/api/posts/instants/",
            {"body": "Tonight only.", "visibility": "public", "lifetime_hours": "24"},
            format="multipart",
        )

        self.assertEqual(create_response.status_code, 201)
        instant = Instant.objects.get(body="Tonight only.")
        self.assertGreater(instant.expires_at, timezone.now())

        self.client.force_authenticate(self.fan)
        report_response = self.client.post(
            f"/api/posts/instants/{instant.id}/report/",
            {"reason": "Spam"},
            format="json",
        )

        self.assertEqual(report_response.status_code, 201)
        self.assertTrue(InstantReport.objects.filter(instant=instant, reporter=self.fan).exists())

    def test_instant_text_limits_are_enforced(self):
        self.client.force_authenticate(self.artist)

        pov_response = self.client.post("/api/posts/pov/", {"body": "x" * 501}, format="multipart")
        instant_response = self.client.post(
            "/api/posts/instants/",
            {"body": "x" * 281, "visibility": "public"},
            format="multipart",
        )

        self.assertEqual(pov_response.status_code, 400)
        self.assertEqual(instant_response.status_code, 400)
