from django.db import migrations, models

import artists.themes


class Migration(migrations.Migration):

    dependencies = [
        ("artists", "0017_artistprofile_is_featured"),
    ]

    operations = [
        migrations.AddField(
            model_name="artistprofile",
            name="theme_name",
            field=models.CharField(
                choices=artists.themes.THEME_CHOICES,
                default=artists.themes.DEFAULT_THEME,
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name="artistprofile",
            name="studio_theme_name",
            field=models.CharField(
                choices=artists.themes.THEME_CHOICES,
                default=artists.themes.DEFAULT_THEME,
                max_length=40,
            ),
        ),
    ]
