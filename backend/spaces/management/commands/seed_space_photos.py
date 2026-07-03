from django.core.management.base import BaseCommand

from spaces.placeholder_photos import ensure_all_listing_galleries


class Command(BaseCommand):
    help = "Add generic stage and bar photos to space listings that have no gallery yet."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Replace existing gallery photos on every listing.",
        )

    def handle(self, *args, **options):
        listings_updated, total_photos = ensure_all_listing_galleries(force=options["force"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {listings_updated} listing(s) with {total_photos} photo(s)."
            )
        )
