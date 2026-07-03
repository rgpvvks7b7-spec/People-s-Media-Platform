from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("artists", "0010_artistprofessionprofile"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ArtistFanContact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email_shared", models.BooleanField(default=False)),
                ("shared_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("signup_opt_in", "Signup opt-in"),
                            ("support_prompt", "Support prompt"),
                            ("manual", "Manual"),
                        ],
                        default="manual",
                        max_length=40,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "artist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fan_contacts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "fan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="artist_contact_permissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-shared_at", "-created_at"],
                "unique_together": {("artist", "fan")},
            },
        ),
    ]
