import csv
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from artists.models import ArtistProfile


User = get_user_model()


class Command(BaseCommand):
    help = "Mark launch artists as featured from a CSV (username,is_featured)."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            nargs="?",
            default="",
            help="Optional CSV with columns: username,is_featured (true/false)",
        )

    def handle(self, *args, **options):
        csv_path = (options.get("csv_path") or "").strip()
        if not csv_path:
            featured = ArtistProfile.objects.filter(owner__user_type=User.ARTIST).order_by("-created_at")[:15]
            count = featured.update(is_featured=True)
            self.stdout.write(self.style.SUCCESS(f"Marked {count} recent artists as featured."))
            return

        path = Path(csv_path)
        if not path.exists():
            self.stderr.write(f"CSV not found: {path}")
            return

        updated = 0
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                username = (row.get("username") or "").strip()
                if not username:
                    continue
                featured = str(row.get("is_featured", "true")).lower() in {"1", "true", "yes", "on"}
                try:
                    user = User.objects.get(username=username, user_type=User.ARTIST)
                except User.DoesNotExist:
                    self.stderr.write(f"Artist not found: {username}")
                    continue
                profile, _ = ArtistProfile.objects.get_or_create(owner=user, defaults={"stage_name": user.display_name or username})
                profile.is_featured = featured
                profile.save(update_fields=["is_featured"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Updated {updated} artist profiles from {path}."))
