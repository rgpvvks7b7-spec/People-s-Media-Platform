from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from artists.models import ArtistProfile
from posts.models import Comment, Like, Post
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

    def test_fans_cannot_create_posts_but_artists_can(self):
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
