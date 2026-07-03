from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("artists", "0008_artistprofile_instagram_reach_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="artistprofile",
            name="professions",
            field=models.CharField(default="music", max_length=255),
        ),
    ]
