from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0004_post_external_provider_post_external_url_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
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
