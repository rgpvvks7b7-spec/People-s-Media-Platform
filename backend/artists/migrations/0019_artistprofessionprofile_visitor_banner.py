from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("artists", "0018_artistprofile_themes"),
    ]

    operations = [
        migrations.AddField(
            model_name="artistprofessionprofile",
            name="visitor_banner",
            field=models.FileField(blank=True, null=True, upload_to="artist_visitor_banners/"),
        ),
        migrations.AddField(
            model_name="artistprofessionprofile",
            name="visitor_banner_duration_seconds",
            field=models.PositiveSmallIntegerField(
                choices=[(15, "15 seconds"), (30, "30 seconds"), (45, "45 seconds")],
                default=30,
            ),
        ),
    ]
