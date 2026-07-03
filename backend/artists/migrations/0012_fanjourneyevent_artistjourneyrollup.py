from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("artists", "0011_artistfancontact"),
        ("mediahub", "0005_songcoverart_musicupload_library_cover"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FanJourneyEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("page_view", "Page view"),
                            ("follow", "Follow"),
                            ("subscribe", "Subscribe"),
                            ("tip", "Tip"),
                            ("purchase", "Purchase"),
                            ("music_preview", "Music preview"),
                            ("music_full_play", "Music full play"),
                            ("email_opt_in", "Email opt-in"),
                            ("unsubscribe", "Unsubscribe"),
                            ("content_engagement", "Content engagement"),
                        ],
                        max_length=40,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("occurred_at", models.DateTimeField(auto_now_add=True)),
                (
                    "artist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="artist_journey_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "fan",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="fan_journey_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "music_upload",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="journey_events",
                        to="mediahub.musicupload",
                    ),
                ),
            ],
            options={
                "ordering": ["-occurred_at"],
                "indexes": [
                    models.Index(fields=["artist", "event_type", "occurred_at"], name="artists_fan_artist__587828_idx"),
                    models.Index(fields=["fan", "artist", "occurred_at"], name="artists_fan_fan_id_7ba14c_idx"),
                    models.Index(fields=["music_upload", "event_type", "occurred_at"], name="artists_fan_music_u_5ef3be_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ArtistJourneyRollup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period", models.CharField(choices=[("daily", "Daily"), ("weekly", "Weekly")], default="daily", max_length=20)),
                ("period_start", models.DateField()),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("page_view", "Page view"),
                            ("follow", "Follow"),
                            ("subscribe", "Subscribe"),
                            ("tip", "Tip"),
                            ("purchase", "Purchase"),
                            ("music_preview", "Music preview"),
                            ("music_full_play", "Music full play"),
                            ("email_opt_in", "Email opt-in"),
                            ("unsubscribe", "Unsubscribe"),
                            ("content_engagement", "Content engagement"),
                        ],
                        max_length=40,
                    ),
                ),
                ("count", models.PositiveIntegerField(default=0)),
                (
                    "artist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="journey_rollups",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("artist", "period", "period_start", "event_type")},
                "indexes": [
                    models.Index(fields=["artist", "period", "period_start"], name="artists_art_artist__637fea_idx"),
                ],
            },
        ),
    ]
