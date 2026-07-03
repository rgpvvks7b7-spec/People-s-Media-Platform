from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0009_alter_product_product_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
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
