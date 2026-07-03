from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0004_fansubscription_profession"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OneTimeTip",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("profession", models.CharField(choices=[("music", "Music"), ("visual_art", "Painting / Drawing"), ("digital_art", "Digital Art"), ("craft", "Crafts"), ("writing", "Writing"), ("performance", "Performance"), ("other", "Other")], default="music", max_length=40)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=8)),
                ("artist_share", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=8)),
                ("platform_fee", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=8)),
                ("message", models.CharField(blank=True, max_length=240)),
                ("is_public", models.BooleanField(default=True)),
                ("payment_provider", models.CharField(blank=True, default="demo", max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("artist", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tips_received", to=settings.AUTH_USER_MODEL)),
                ("fan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tips_sent", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
