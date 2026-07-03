from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_user_artist_plan"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_share_consent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="share_email_with_supported_artists",
            field=models.BooleanField(default=False),
        ),
    ]
