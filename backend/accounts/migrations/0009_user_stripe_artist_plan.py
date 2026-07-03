from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_user_discovery_controls"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="stripe_artist_customer_id",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="user",
            name="stripe_artist_subscription_id",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
