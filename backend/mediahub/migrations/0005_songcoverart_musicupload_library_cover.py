import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mediahub", "0004_musicupload_allow_fan_radio_fanplaylist_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SongCoverArt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("profession", models.CharField(choices=[("music", "Music"), ("visual_art", "Visual Art"), ("photography", "Photography"), ("writing", "Writing"), ("craft", "Craft")], default="music", max_length=40)),
                ("image", models.ImageField(upload_to="cover_art/library/")),
                ("label", models.CharField(blank=True, max_length=120)),
                ("is_default", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("artist", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="song_cover_art", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-is_default", "-created_at"],
            },
        ),
        migrations.AddField(
            model_name="musicupload",
            name="library_cover",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tracks", to="mediahub.songcoverart"),
        ),
    ]
