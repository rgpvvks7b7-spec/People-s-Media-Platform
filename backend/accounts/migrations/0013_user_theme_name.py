from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_user_session_login_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="theme_name",
            field=models.CharField(
                choices=[
                    ("theme-indie-dark", "IndieFund Dark"),
                    ("theme-retro-vhs", "Retro VHS"),
                    ("theme-clean-label", "Clean Label"),
                    ("theme-boombap", "Boom Bap"),
                    ("theme-neon-club", "Neon Club"),
                    ("theme-tribute-purple-rain", "Tribute: Purple Rain"),
                    ("theme-tribute-alien-pop", "Tribute: Alien Pop"),
                    ("theme-tribute-gold-frame", "Tribute: Gold Frame Soul"),
                    ("theme-tribute-starman", "Tribute: Starman Sky"),
                    ("theme-tribute-neon-angel", "Tribute: Neon Angel"),
                    ("theme-tribute-midnight-piano", "Tribute: Midnight Piano"),
                ],
                default="theme-indie-dark",
                max_length=40,
            ),
        ),
    ]
