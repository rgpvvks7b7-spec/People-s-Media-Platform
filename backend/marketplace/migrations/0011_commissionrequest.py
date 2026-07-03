from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0010_product_profession"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CommissionRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("profession", models.CharField(choices=[("music", "Music"), ("visual_art", "Painting / Drawing"), ("digital_art", "Digital Art"), ("craft", "Crafts"), ("writing", "Writing"), ("performance", "Performance"), ("other", "Other")], default="visual_art", max_length=40)),
                ("title", models.CharField(max_length=160)),
                ("brief", models.TextField()),
                ("budget", models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ("deadline", models.DateField(blank=True, null=True)),
                ("size_format", models.CharField(blank=True, max_length=120)),
                ("reference_notes", models.TextField(blank=True)),
                ("reference_links", models.TextField(blank=True)),
                ("delivery_notes", models.TextField(blank=True)),
                ("shipping_required", models.BooleanField(default=False)),
                ("status", models.CharField(choices=[("new", "New"), ("reviewing", "Reviewing"), ("accepted", "Accepted"), ("declined", "Declined"), ("completed", "Completed")], default="new", max_length=40)),
                ("artist_response", models.TextField(blank=True)),
                ("quoted_price", models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("artist", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="commission_inquiries", to=settings.AUTH_USER_MODEL)),
                ("fan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="commission_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
    ]
