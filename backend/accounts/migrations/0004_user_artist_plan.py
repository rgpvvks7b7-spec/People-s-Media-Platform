from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_user_beta_fields_betafeedback"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="artist_plan",
            field=models.CharField(default="free", max_length=40),
        ),
    ]
