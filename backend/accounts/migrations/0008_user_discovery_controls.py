from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_user_cover_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="discovery_prefer_emerging",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="discovery_fewer_promoted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="discovery_promoted_genres_only",
            field=models.BooleanField(default=False),
        ),
    ]
