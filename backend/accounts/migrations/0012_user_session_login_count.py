from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_user_terms_accepted_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="session_login_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
