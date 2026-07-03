from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("artists", "0016_remove_artistprofile_instagram_reach_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="artistprofile",
            name="is_featured",
            field=models.BooleanField(default=False),
        ),
    ]
