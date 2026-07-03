from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mediahub", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="musicupload",
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
    ]
