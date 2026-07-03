from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("mediahub", "0008_alter_artworkupload_profession_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("discovery", "0002_artistsignal_signal_type_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="TrackSignal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("signal_type", models.CharField(choices=[("save", "Save"), ("skip", "Skip")], default="save", max_length=40)),
                ("liked_genre", models.CharField(blank=True, max_length=80)),
                ("weight", models.FloatField(default=1.0)),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("fan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="track_discovery_signals", to=settings.AUTH_USER_MODEL)),
                ("track", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="discovery_signals", to="mediahub.musicupload")),
            ],
            options={
                "unique_together": {("fan", "track", "signal_type")},
            },
        ),
    ]
