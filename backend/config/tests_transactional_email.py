from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from config.transactional_email import build_verification_email, email_delivery_configured


class TransactionalEmailTests(TestCase):
    def test_build_verification_email_contains_link(self):
        user = type("User", (), {"username": "fan", "display_name": "Fan", "email": "fan@example.com"})()
        subject, body = build_verification_email(user, "https://example.com/?verify-email=abc")
        self.assertIn("Verify your IndieFund email", subject)
        self.assertIn("verify-email=abc", body)

    @override_settings(
        DEBUG=False,
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="smtp.example.com",
        DEFAULT_FROM_EMAIL="IndieFund <noreply@example.com>",
    )
    def test_email_delivery_configured_for_smtp(self):
        self.assertTrue(email_delivery_configured())

    @override_settings(
        DEBUG=False,
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
    )
    def test_test_transactional_email_rejects_console_backend(self):
        with self.assertRaises(CommandError):
            call_command("test_transactional_email", "--to=test@example.com", stdout=StringIO())

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="IndieFund <noreply@example.com>",
    )
    def test_test_transactional_email_sends_samples(self):
        out = StringIO()
        call_command("test_transactional_email", "--to=sample@example.com", stdout=out)
        self.assertIn("3 transactional test email", out.getvalue())
