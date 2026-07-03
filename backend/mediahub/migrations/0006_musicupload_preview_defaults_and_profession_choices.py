from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mediahub", "0005_songcoverart_musicupload_library_cover"),
    ]

    operations = [
        migrations.AlterField(
            model_name="songcoverart",
            name="profession",
            field=models.CharField(
                choices=[
                    ("music", "Music"),
                    ("visual_art", "Painting / Drawing"),
                    ("digital_art", "Digital Art"),
                    ("craft", "Crafts"),
                    ("writing", "Writing"),
                    ("performance", "Performance"),
                    ("other", "Other"),
                ],
                default="music",
                max_length=40,
            ),
        ),
        migrations.AlterField(
            model_name="musicupload",
            name="is_subscriber_only",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="musicupload",
            name="preview_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="musicupload",
            name="preview_seconds",
            field=models.PositiveSmallIntegerField(default=30),
        ),
    ]
