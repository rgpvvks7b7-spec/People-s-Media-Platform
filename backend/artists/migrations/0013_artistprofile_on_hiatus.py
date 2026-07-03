from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("artists", "0012_fanjourneyevent_artistjourneyrollup"),
    ]

    operations = [
        migrations.AddField(
            model_name="artistprofile",
            name="on_hiatus",
            field=models.BooleanField(default=False),
        ),
    ]
