from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0003_fansubscription_payment_provider_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="fansubscription",
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
        migrations.AlterUniqueTogether(
            name="fansubscription",
            unique_together={("fan", "artist", "profession")},
        ),
    ]
