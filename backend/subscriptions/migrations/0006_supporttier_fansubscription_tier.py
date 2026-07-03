from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0005_onetimetip"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SupportTier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("profession", models.CharField(choices=[("music", "Music"), ("visual_art", "Painting / Drawing"), ("digital_art", "Digital Art"), ("craft", "Crafts"), ("writing", "Writing"), ("performance", "Performance"), ("other", "Other")], default="music", max_length=40)),
                ("name", models.CharField(max_length=80)),
                ("description", models.TextField(blank=True)),
                ("monthly_amount", models.DecimalField(decimal_places=2, default=Decimal("1.00"), max_digits=8)),
                ("benefits", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("artist", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="support_tiers", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["monthly_amount", "created_at"],
            },
        ),
        migrations.AddField(
            model_name="fansubscription",
            name="tier",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="subscriptions", to="subscriptions.supporttier"),
        ),
    ]
