from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from artists.models import ArtistProfile
from artists.models import ArtistFanContact
from accounts.models import BetaFeedback
from accounts.beta_report import build_beta_feedback_report
from subscriptions.models import FanSubscription


User = get_user_model()


def register_payload(**fields):
    payload = {"terms_accepted": True}
    payload.update(fields)
    return payload


class AccountSetupTests(APITestCase):
    def test_fan_registration_saves_discovery_preferences_and_logs_in(self):
        response = self.client.post(
            "/api/accounts/register/",
            register_payload(
                username="fan_setup",
                password="password123",
                display_name="Fan Setup",
                email="fan_setup@example.com",
                user_type=User.FAN,
                favorite_genres="indie pop, dream pop",
                discovery_location="Melbourne",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["user"]["user_type"], User.FAN)
        self.assertEqual(response.data["user"]["favorite_genres"], "indie pop, dream pop")
        self.assertEqual(response.data["user"]["discovery_location"], "Melbourne")

        current_user_response = self.client.get("/api/accounts/current-user/")
        self.assertTrue(current_user_response.data["authenticated"])
        self.assertEqual(current_user_response.data["user"]["username"], "fan_setup")
        self.assertEqual(current_user_response.data["user"]["session_login_count"], 1)

    def test_login_increments_session_login_count(self):
        User.objects.create_user(
            username="login_counter",
            password="password123",
            user_type=User.FAN,
            display_name="Login Counter",
            email="login_counter@example.com",
        )

        first = self.client.post(
            "/api/accounts/login/",
            {"username": "login_counter", "password": "password123"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["user"]["session_login_count"], 1)

        second = self.client.post(
            "/api/accounts/login/",
            {"username": "login_counter", "password": "password123"},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["user"]["session_login_count"], 2)

    def test_artist_registration_creates_profile_for_dashboard_navigation(self):
        response = self.client.post(
            "/api/accounts/register/",
            register_payload(
                username="artist_setup",
                password="password123",
                display_name="Artist Setup",
                email="artist_setup@example.com",
                user_type=User.ARTIST,
                stage_name="Setup Stage",
                genre="Indie Rock",
                city="Sydney",
                artist_story="Testing a complete artist setup profile.",
                influences="The Beths, Wet Leg",
                professions=["music", "visual_art"],
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["user"]["is_artist"])
        self.assertIsNotNone(response.data["user"]["artist_profile_id"])

        profile = ArtistProfile.objects.get(owner__username="artist_setup")
        self.assertEqual(profile.stage_name, "Setup Stage")
        self.assertEqual(profile.genre, "Indie Rock")
        self.assertEqual(profile.city, "Sydney")
        self.assertEqual(profile.profession_list(), ["music", "visual_art"])

    def test_artist_registration_accepts_new_phase_five_professions(self):
        response = self.client.post(
            "/api/accounts/register/",
            register_payload(
                username="phase_five_artist",
                password="password123",
                display_name="Phase Five",
                email="phase_five@example.com",
                user_type=User.ARTIST,
                stage_name="Phase Five",
                genre="Comedy",
                city="Melbourne",
                professions=["comedy", "podcast", "film"],
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        profile = ArtistProfile.objects.get(owner__username="phase_five_artist")
        self.assertEqual(profile.profession_list(), ["comedy", "podcast", "film"])
        self.assertEqual(ArtistProfile.profession_label("comedy"), "Comedian")

    def test_host_registration_creates_discoverable_host_profile(self):
        from spaces.models import HostProfile

        response = self.client.post(
            "/api/accounts/register/",
            register_payload(
                username="venue_setup",
                password="password123",
                display_name="The Back Room",
                email="bookings@backroom.example.com",
                user_type=User.HOST,
                discovery_location="Melbourne",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["user"]["is_host"])

        profile = HostProfile.objects.get(user__username="venue_setup")
        self.assertEqual(profile.business_name, "The Back Room")
        self.assertEqual(profile.city, "Melbourne")
        self.assertEqual(profile.contact_email, "bookings@backroom.example.com")

    def test_duplicate_username_returns_clear_setup_error(self):
        User.objects.create_user(username="taken", password="password123")

        response = self.client.post(
            "/api/accounts/register/",
            register_payload(
                username="taken",
                password="password123",
                display_name="Taken User",
                email="taken@example.com",
                user_type=User.FAN,
                favorite_genres="indie pop",
                discovery_location="Melbourne",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Username is already taken")

    def test_registration_requires_terms_acceptance(self):
        response = self.client.post(
            "/api/accounts/register/",
            {
                "username": "no_terms_fan",
                "password": "password123",
                "display_name": "No Terms",
                "email": "no_terms@example.com",
                "user_type": User.FAN,
                "favorite_genres": "indie pop",
                "discovery_location": "Melbourne",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Terms of Service", response.data["error"])

    def test_authenticated_user_can_submit_beta_feedback(self):
        user = User.objects.create_user(
            username="beta_fan",
            password="password123",
            user_type=User.FAN,
        )
        self.client.force_authenticate(user)

        response = self.client.post(
            "/api/accounts/beta-feedback/",
            {
                "category": "navigation",
                "severity": "high",
                "path": "/?page=saved",
                "summary": "Saved page needs clearer next action",
                "details": "I saved an artist but did not know whether to follow, play, or support next.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["feedback"]["category"], BetaFeedback.NAVIGATION)
        self.assertEqual(response.data["feedback"]["severity"], BetaFeedback.HIGH)

        user.refresh_from_db()
        self.assertTrue(user.is_beta_tester)
        self.assertTrue(BetaFeedback.objects.filter(user=user).exists())

    def test_beta_feedback_requires_summary(self):
        user = User.objects.create_user(username="beta_empty", password="password123")
        self.client.force_authenticate(user)

        response = self.client.post(
            "/api/accounts/beta-feedback/",
            {"category": "setup", "details": "Missing summary"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Summary is required")

    def test_user_can_list_their_own_beta_feedback(self):
        user = User.objects.create_user(username="beta_list", password="password123")
        other_user = User.objects.create_user(username="other_beta", password="password123")
        BetaFeedback.objects.create(
            user=user,
            category=BetaFeedback.SETUP,
            severity=BetaFeedback.MEDIUM,
            summary="Setup checklist would help",
        )
        BetaFeedback.objects.create(
            user=other_user,
            category=BetaFeedback.NAVIGATION,
            severity=BetaFeedback.BLOCKER,
            summary="Other user's feedback",
        )
        self.client.force_authenticate(user)

        response = self.client.get("/api/accounts/beta-feedback/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["summary"], "Setup checklist would help")

    def test_admin_can_view_beta_feedback_summary(self):
        admin = User.objects.create_user(
            username="beta_admin_test",
            password="password123",
            user_type=User.ADMIN,
            is_staff=True,
        )
        fan = User.objects.create_user(username="beta_fan_test", password="password123", user_type=User.FAN)
        BetaFeedback.objects.create(
            user=fan,
            category=BetaFeedback.NAVIGATION,
            severity=BetaFeedback.BLOCKER,
            summary="Blocker issue",
        )
        BetaFeedback.objects.create(
            user=fan,
            category=BetaFeedback.SETUP,
            severity=BetaFeedback.MEDIUM,
            summary="Setup note",
        )

        self.client.force_authenticate(fan)
        denied = self.client.get("/api/accounts/beta-feedback/summary/")
        self.assertEqual(denied.status_code, 403)

        self.client.force_authenticate(admin)
        response = self.client.get("/api/accounts/beta-feedback/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_feedback"], 2)
        self.assertEqual(len(response.data["blockers"]), 1)
        self.assertEqual(response.data["blockers"][0]["summary"], "Blocker issue")

    def test_admin_can_resolve_beta_feedback(self):
        admin = User.objects.create_user(
            username="triage_admin",
            password="password123",
            user_type=User.ADMIN,
            is_staff=True,
        )
        fan = User.objects.create_user(username="triage_fan", password="password123", user_type=User.FAN)
        feedback = BetaFeedback.objects.create(
            user=fan,
            category=BetaFeedback.NAVIGATION,
            severity=BetaFeedback.BLOCKER,
            summary="Triage me",
        )

        self.client.force_authenticate(admin)
        response = self.client.post(
            f"/api/accounts/beta-feedback/{feedback.id}/resolve/",
            {"resolved": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["feedback"]["resolved"])
        self.assertEqual(response.data["summary"]["unresolved_count"], 0)
        feedback.refresh_from_db()
        self.assertTrue(feedback.resolved)

        reopen = self.client.post(
            f"/api/accounts/beta-feedback/{feedback.id}/resolve/",
            {"resolved": False},
            format="json",
        )
        self.assertEqual(reopen.status_code, 200)
        self.assertFalse(reopen.data["feedback"]["resolved"])
        self.assertEqual(reopen.data["summary"]["unresolved_count"], 1)

    def test_non_admin_cannot_resolve_beta_feedback(self):
        fan = User.objects.create_user(username="nosey_fan", password="password123", user_type=User.FAN)
        feedback = BetaFeedback.objects.create(
            user=fan,
            category=BetaFeedback.OTHER,
            severity=BetaFeedback.LOW,
            summary="Should stay open",
        )

        self.client.force_authenticate(fan)
        response = self.client.post(
            f"/api/accounts/beta-feedback/{feedback.id}/resolve/",
            {"resolved": True},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        feedback.refresh_from_db()
        self.assertFalse(feedback.resolved)

    def test_beta_feedback_report_aggregates_counts(self):
        fan = User.objects.create_user(username="report_fan", password="password123", user_type=User.FAN, is_beta_tester=True)
        BetaFeedback.objects.create(
            user=fan,
            category=BetaFeedback.PAYMENTS,
            severity=BetaFeedback.HIGH,
            summary="Payments issue",
        )

        report = build_beta_feedback_report()
        self.assertGreaterEqual(report["total_feedback"], 1)
        self.assertEqual(report["by_category"]["payments"]["count"], 1)
        self.assertEqual(report["by_severity"]["high"]["count"], 1)

    def test_artist_plans_are_available_for_upgrade_surface(self):
        response = self.client.get("/api/accounts/artist-plans/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["free"]["id"], "free")
        self.assertEqual(response.data["paid"][0]["id"], "pro")
        self.assertEqual(response.data["paid"][1]["id"], "studio")
        self.assertEqual(response.data["paid"][1]["monthly_promotion_credits"], "25.00")

    @override_settings(DEBUG=True)
    def test_demo_studio_upgrade_grants_promotion_credits(self):
        artist = User.objects.create_user(
            username="studio_artist",
            password="password123",
            email="studio@example.com",
            user_type=User.ARTIST,
        )
        ArtistProfile.objects.create(owner=artist, stage_name="Studio Artist", genre="pop", city="Melbourne")
        self.client.force_authenticate(artist)

        response = self.client.post(
            "/api/accounts/artist-plan/",
            {"plan": "studio"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["artist_plan"], "studio")
        self.assertEqual(response.data["studio_credits_granted"], "25.00")
        self.assertEqual(response.data["promotion_balance"], "25.00")

    @override_settings(DEBUG=True, STRIPE_SECRET_KEY="")
    def test_artist_plan_checkout_demo_activates_studio(self):
        artist = User.objects.create_user(
            username="checkout_artist",
            password="password123",
            email="checkout@example.com",
            user_type=User.ARTIST,
        )
        ArtistProfile.objects.create(owner=artist, stage_name="Checkout Artist", genre="pop", city="Melbourne")
        self.client.force_authenticate(artist)

        response = self.client.post(
            "/api/accounts/artist-plan/checkout/",
            {"plan": "studio"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["demo"])
        self.assertEqual(response.data["user"]["artist_plan"], "studio")
        self.assertEqual(response.data["studio_credits_granted"], "25.00")

    def test_artist_plan_checkout_requires_artist(self):
        fan = User.objects.create_user(
            username="plan_fan",
            password="password123",
            user_type=User.FAN,
        )
        self.client.force_authenticate(fan)
        response = self.client.post(
            "/api/accounts/artist-plan/checkout/",
            {"plan": "pro"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_fan_registration_can_record_email_share_consent(self):
        response = self.client.post(
            "/api/accounts/register/",
            register_payload(
                username="email_fan",
                password="password123",
                display_name="Email Fan",
                email="fan@example.com",
                user_type=User.FAN,
                favorite_genres="indie pop",
                discovery_location="Melbourne",
                share_email_with_supported_artists=True,
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="email_fan")
        self.assertTrue(user.share_email_with_supported_artists)
        self.assertIsNotNone(user.email_share_consent_at)

    def test_global_email_revoke_preserves_artist_contact_audit(self):
        fan = User.objects.create_user(
            username="revoke_fan",
            password="password123",
            email="revoke@example.com",
            user_type=User.FAN,
            share_email_with_supported_artists=True,
        )
        artist = User.objects.create_user(username="revoke_artist", password="password123", user_type=User.ARTIST)
        ArtistProfile.objects.create(owner=artist, stage_name="Revoke Artist")
        FanSubscription.objects.create(fan=fan, artist=artist, active=True)
        ArtistFanContact.objects.create(fan=fan, artist=artist, email_shared=True)
        self.client.force_authenticate(fan)

        response = self.client.post(
            "/api/accounts/email-preferences/",
            {"share_email_with_supported_artists": False},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        contact = ArtistFanContact.objects.get(fan=fan, artist=artist)
        self.assertFalse(contact.email_shared)
        self.assertIsNotNone(contact.revoked_at)


class ProfileMediaTests(APITestCase):
    def test_fan_can_upload_avatar_and_cover(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        fan = User.objects.create_user(username="photo_fan", password="password123", user_type=User.FAN)
        self.client.force_authenticate(fan)

        avatar = SimpleUploadedFile("avatar.png", b"fake-image-bytes", content_type="image/png")
        cover = SimpleUploadedFile("cover.png", b"fake-image-bytes", content_type="image/png")

        response = self.client.post(
            "/api/accounts/profile-media/",
            {"avatar": avatar, "cover_image": cover},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["user"]["avatar"])
        self.assertIsNotNone(response.data["user"]["cover_image"])

        fan.refresh_from_db()
        self.assertTrue(fan.avatar)
        self.assertTrue(fan.cover_image)

    def test_profile_media_requires_image(self):
        fan = User.objects.create_user(username="no_photo_fan", password="password123", user_type=User.FAN)
        self.client.force_authenticate(fan)

        response = self.client.post("/api/accounts/profile-media/", {}, format="multipart")

        self.assertEqual(response.status_code, 400)

    def test_profile_media_requires_authentication(self):
        response = self.client.post("/api/accounts/profile-media/", {}, format="multipart")
        self.assertEqual(response.status_code, 401)


class HealthCheckTests(APITestCase):
    def test_health_endpoint_reports_database_ok(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertTrue(response.json()["database"])

    def test_health_endpoint_needs_no_authentication(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)


PROD_SAFE_SETTINGS = dict(
    DEBUG=False,
    SECRET_KEY="a-strong-unique-production-secret-key-value",
    ALLOWED_HOSTS=["indiefund.example.com"],
    SECURE_SSL_REDIRECT=True,
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    SECURE_HSTS_SECONDS=31536000,
    STRIPE_WEBHOOK_SECRET="whsec_test",
    EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
    EMAIL_HOST="smtp.example.com",
    DEFAULT_FROM_EMAIL="IndieFund <noreply@example.com>",
    API_THROTTLE_ENABLED=True,
    REST_FRAMEWORK={
        "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
        "DEFAULT_THROTTLE_RATES": {
            "anon": "120/min",
            "auth": "20/min",
            "checkout": "30/min",
            "upload": "30/min",
        },
    },
)


class SecurityCheckCommandTests(APITestCase):
    def test_strict_mode_passes_with_production_safe_settings(self):
        from io import StringIO
        from django.core.management import call_command

        with override_settings(**PROD_SAFE_SETTINGS):
            out = StringIO()
            call_command("beta_security_check", "--strict", stdout=out)
            self.assertIn("All checks passed", out.getvalue())

    def test_strict_mode_fails_when_misconfigured(self):
        from io import StringIO
        from django.core.management import call_command
        from django.core.management.base import CommandError

        unsafe = dict(PROD_SAFE_SETTINGS)
        unsafe["SECRET_KEY"] = "dev-only-change-this"
        unsafe["SECURE_SSL_REDIRECT"] = False
        with override_settings(**unsafe):
            with self.assertRaises(CommandError):
                call_command("beta_security_check", "--strict", stdout=StringIO())

    def test_non_strict_mode_never_raises(self):
        from io import StringIO
        from django.core.management import call_command

        unsafe = dict(PROD_SAFE_SETTINGS)
        unsafe["DEBUG"] = False
        unsafe["SECRET_KEY"] = "dev-only-change-this"
        with override_settings(**unsafe):
            call_command("beta_security_check", stdout=StringIO())


class ProfileThemeTests(APITestCase):
    def setUp(self):
        self.fan = User.objects.create_user(
            username="theme_fan",
            password="password123",
            user_type=User.FAN,
            display_name="Theme Fan",
            email="theme_fan@example.com",
        )
        self.artist = User.objects.create_user(
            username="theme_artist",
            password="password123",
            user_type=User.ARTIST,
            display_name="Theme Artist",
            email="theme_artist@example.com",
        )
        ArtistProfile.objects.create(owner=self.artist, stage_name="Theme Artist")

    def test_fan_can_save_profile_theme(self):
        self.client.force_login(self.fan)

        response = self.client.post(
            "/api/accounts/profile-theme/",
            {"theme_name": "theme-neon-club"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["theme_name"], "theme-neon-club")
        self.fan.refresh_from_db()
        self.assertEqual(self.fan.theme_name, "theme-neon-club")

    def test_invalid_theme_falls_back_to_default(self):
        self.client.force_login(self.fan)

        response = self.client.post(
            "/api/accounts/profile-theme/",
            {"theme_name": "theme-not-real"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["theme_name"], "theme-indie-dark")

    def test_fan_can_save_accessible_theme(self):
        self.client.force_login(self.fan)

        response = self.client.post(
            "/api/accounts/profile-theme/",
            {"theme_name": "theme-accessible-dark"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["theme_name"], "theme-accessible-dark")

    def test_artist_cannot_use_fan_profile_theme_endpoint(self):
        self.client.force_login(self.artist)

        response = self.client.post(
            "/api/accounts/profile-theme/",
            {"theme_name": "theme-neon-club"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("page settings", response.data["error"])

    def test_host_can_save_venue_theme(self):
        host = User.objects.create_user(
            username="theme_host",
            password="password123",
            user_type=User.HOST,
            display_name="Theme Host",
            email="theme_host@example.com",
        )
        self.client.force_login(host)

        response = self.client.post(
            "/api/accounts/profile-theme/",
            {"theme_name": "theme-host-velvet-lounge"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["theme_name"], "theme-host-velvet-lounge")
        host.refresh_from_db()
        self.assertEqual(host.theme_name, "theme-host-velvet-lounge")

    def test_fan_cannot_save_host_only_theme(self):
        self.client.force_login(self.fan)

        response = self.client.post(
            "/api/accounts/profile-theme/",
            {"theme_name": "theme-host-coffee-house"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["theme_name"], "theme-indie-dark")
        self.fan.refresh_from_db()
        self.assertEqual(self.fan.theme_name, "theme-indie-dark")

    def test_host_cannot_save_fan_platform_theme(self):
        host = User.objects.create_user(
            username="theme_host_strict",
            password="password123",
            user_type=User.HOST,
            display_name="Theme Host Strict",
            email="theme_host_strict@example.com",
        )
        self.client.force_login(host)

        response = self.client.post(
            "/api/accounts/profile-theme/",
            {"theme_name": "theme-neon-club"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["theme_name"], "theme-host-warm-hearth")
        host.refresh_from_db()
        self.assertEqual(host.theme_name, "theme-host-warm-hearth")

    def test_host_can_save_accessible_theme(self):
        host = User.objects.create_user(
            username="theme_host_a11y",
            password="password123",
            user_type=User.HOST,
            display_name="Theme Host A11y",
            email="theme_host_a11y@example.com",
        )
        self.client.force_login(host)

        response = self.client.post(
            "/api/accounts/profile-theme/",
            {"theme_name": "theme-host-accessible-charcoal"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["theme_name"], "theme-host-accessible-charcoal")
        host.refresh_from_db()
        self.assertEqual(host.theme_name, "theme-host-accessible-charcoal")
