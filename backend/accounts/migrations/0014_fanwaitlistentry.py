from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_user_theme_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="FanWaitlistEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("city", models.CharField(blank=True, max_length=120)),
                ("favorite_genres", models.CharField(blank=True, max_length=255)),
                ("source", models.CharField(default="prelaunch", max_length=40)),
                ("confirmed", models.BooleanField(default=False)),
                ("confirmation_token", models.CharField(blank=True, default="", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
