from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("spaces", "0014_spacefollow"),
    ]

    operations = [
        migrations.AddField(
            model_name="spacebooking",
            name="series_id",
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
    ]
