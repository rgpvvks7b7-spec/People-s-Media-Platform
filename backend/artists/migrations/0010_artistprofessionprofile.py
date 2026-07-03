from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("artists", "0009_artistprofile_professions"),
    ]

    operations = [
        migrations.CreateModel(
            name="ArtistProfessionProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("profession", models.CharField(choices=[("music", "Music"), ("visual_art", "Painting / Drawing"), ("digital_art", "Digital Art"), ("craft", "Crafts"), ("writing", "Writing"), ("performance", "Performance"), ("other", "Other")], max_length=40)),
                ("display_title", models.CharField(blank=True, max_length=120)),
                ("tagline", models.CharField(blank=True, max_length=160)),
                ("bio", models.TextField(blank=True)),
                ("style", models.CharField(blank=True, max_length=120)),
                ("cover_image", models.ImageField(blank=True, null=True, upload_to="artist_profession_covers/")),
                ("artist_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="profession_profiles", to="artists.artistprofile")),
            ],
            options={
                "ordering": ["profession"],
                "unique_together": {("artist_profile", "profession")},
            },
        ),
    ]
