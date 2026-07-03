from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from config.transactional_email import (
    build_ticket_receipt_email,
    build_verification_email,
    build_waitlist_confirmation_email,
    email_delivery_configured,
    send_platform_email,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Send sample transactional emails (verify, waitlist, receipt) to verify SMTP on staging."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            required=True,
            help="Recipient email address for test messages.",
        )

    def handle(self, *args, **options):
        recipient = (options.get("to") or "").strip().lower()
        if not recipient or "@" not in recipient:
            raise CommandError("Provide a valid --to email address.")

        if not email_delivery_configured():
            raise CommandError(
                f"Email backend not configured for delivery ({settings.EMAIL_BACKEND}). "
                "Set SMTP vars in DEPLOYMENT.md before running this command."
            )

        frontend_url = (settings.FRONTEND_URL or "http://localhost:5173").rstrip("/")
        samples = [
            build_verification_email(
                User(username="sample_user", display_name="Sample User", email=recipient),
                f"{frontend_url}/?verify-email=test-token",
            ),
            build_waitlist_confirmation_email(f"{frontend_url}/?waitlist-confirm=test-token"),
            build_ticket_receipt_email(
                User(username="sample_fan", display_name="Sample Fan", email=recipient),
                type("Product", (), {"title": "Launch Night Ticket", "price": "15.00", "artist": User(username="sample_artist")})(),
                {
                    "amount": "15.00",
                    "show": {
                        "stage_name": "Sample Artist",
                        "venue_name": "Back Bar Stage",
                        "starts_at": "Friday, 1 August · 8:00 PM",
                        "venue_city": "Melbourne",
                        "booking_id": 1,
                    },
                },
                f"{frontend_url}/?page=my-scene&show=1",
            ),
        ]

        sent = 0
        for subject, body in samples:
            send_platform_email(subject=subject, body=body, recipient_list=[recipient])
            sent += 1
            self.stdout.write(self.style.SUCCESS(f"Sent: {subject}"))

        self.stdout.write(self.style.SUCCESS(f"\n{sent} transactional test email(s) sent to {recipient}."))
